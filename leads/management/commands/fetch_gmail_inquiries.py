import email
import imaplib
import logging
import re
from email.utils import parsedate_to_datetime
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from leads.models import Lead, LeadActivity, Ticket


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch emails from Gmail (IMAP) with 'Inquiry/Enquiry' in subject and create leads + tickets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max",
            type=int,
            default=10,
            help="Maximum number of emails to process in one run (default: 10)",
        )
        parser.add_argument(
            "--unseen-only",
            action="store_true",
            default=True,
            help="Only process unseen emails (default: True)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all emails (overrides unseen-only).",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Gmail address to use (overrides settings).",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Gmail app password to use (overrides settings).",
        )
        parser.add_argument(
            "--company_id",
            type=int,
            help="ID of the company to associate leads with.",
        )

    def handle(self, *args, **options):
        max_to_process = options["max"]
        unseen_only = options["unseen_only"]

        # If --all is passed, override to process all emails
        if options.get("all"):
            unseen_only = False

        host = getattr(settings, "GMAIL_IMAP_HOST", "imap.gmail.com")
        port = getattr(settings, "GMAIL_IMAP_PORT", 993)
        email_addr = options.get("email") or getattr(settings, "GMAIL_EMAIL", "")
        app_password = options.get("password") or getattr(settings, "GMAIL_APP_PASSWORD", "")
        company_id = options.get("company_id")

        if not email_addr or not app_password:
            self.stdout.write(
                self.style.ERROR(
                    "GMAIL_EMAIL or GMAIL_APP_PASSWORD not configured.\n"
                    "Configure them in Company settings or settings.py."
                )
            )
            return

        self.stdout.write(self.style.SUCCESS(f"Connecting to Gmail IMAP: {host}:{port} as {email_addr}"))

        try:
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(email_addr, app_password)
        except imaplib.IMAP4.error as e:
            self.stdout.write(self.style.ERROR(f"IMAP login failed: {e}"))
            return

        try:
            subject_filter = getattr(settings, "EMAIL_SUBJECT_FILTER", ["inquiry", "enquiry"])
            processed_count = 0
            total_found = 0
            
            # Check both INBOX and Spam folders
            folders_to_check = ["INBOX", "[Gmail]/Spam"]
            
            for folder_name in folders_to_check:
                try:
                    status, _ = mail.select(folder_name)
                    if status != "OK":
                        self.stdout.write(self.style.WARNING(f"Could not access folder: {folder_name}"))
                        continue
                    
                    self.stdout.write(self.style.NOTICE(f"Checking folder: {folder_name}"))
                    
                    # Build search criteria: unseen or all.
                    # By default, only process UNSEEN emails to avoid duplicates
                    if unseen_only:
                        search_criteria = "(UNSEEN)"
                    else:
                        # If --all is used, still prefer UNSEEN but also check SEEN
                        # We'll process all, but check for duplicates in our database
                        search_criteria = "ALL"
                    
                    status, data = mail.search(None, search_criteria)
                    if status != "OK":
                        self.stdout.write(self.style.WARNING(f"IMAP search failed for {folder_name}: {status} {data}"))
                        continue

                    email_ids = data[0].split()
                    total_found += len(email_ids)
                    
                    # Process emails from this folder (limit total across all folders)
                    emails_to_process = min(len(email_ids), max_to_process - processed_count)
                    if emails_to_process > 0:
                        email_ids = email_ids[-emails_to_process:]  # Get most recent
                    else:
                        continue

                    for eid in email_ids:
                        status, msg_data = mail.fetch(eid, "(RFC822)")
                        if status != "OK":
                            logger.warning("Failed to fetch email id %s", eid)
                            continue

                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)

                        # Get Message-ID to track processed emails
                        message_id = msg.get("Message-ID", "").strip()
                        if not message_id:
                            # Generate a fallback ID from date + from + subject
                            date_header = msg.get("Date", "")
                            message_id = f"{date_header}_{from_header}_{subject}"[:200]

                        subject = email.header.decode_header(msg.get("Subject", ""))[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(errors="ignore")

                        from_header = msg.get("From", "")
                        
                        # Get email date for duplicate checking
                        date_header = msg.get("Date", "")
                        try:
                            email_date = parsedate_to_datetime(date_header) if date_header else None
                        except:
                            email_date = None

                        # Log each email we inspect for debugging
                        self.stdout.write(self.style.NOTICE(f"Inspecting email: From={from_header}, Subject={subject}"))

                        subject_lower = subject.lower() if subject else ""
                        if not any(k.lower() in subject_lower for k in subject_filter):
                            logger.info("Skipping email (subject filter): %s", subject)
                            continue

                        # Extract body (prefer plain text)
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition", ""))
                                if content_type == "text/plain" and "attachment" not in content_disposition:
                                    charset = part.get_content_charset() or "utf-8"
                                    body = part.get_payload(decode=True).decode(charset, errors="ignore")
                                    break
                        else:
                            charset = msg.get_content_charset() or "utf-8"
                            body = msg.get_payload(decode=True).decode(charset, errors="ignore")

                        # ---------- Structured body parsing ----------
                        # Extract sender email from From header (always use this as primary source)
                        sender_name = from_header
                        sender_addr = ""
                        
                        # Parse From header: "Name <email@example.com>" or "email@example.com"
                        if "<" in from_header and ">" in from_header:
                            parts = from_header.split("<")
                            sender_name = parts[0].strip().strip('"')
                            sender_addr = parts[1].split(">")[0].strip()
                        else:
                            # Try to extract email from header if it's just an email address
                            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", from_header)
                            if email_match:
                                sender_addr = email_match.group(0)
                                sender_name = from_header.replace(sender_addr, "").strip().strip('"')
                            else:
                                # Fallback: use header as-is, but this shouldn't happen
                                sender_addr = from_header
                        
                        # Ensure we have a valid email address
                        if not sender_addr or "@" not in sender_addr:
                            self.stdout.write(self.style.WARNING(f"Could not extract valid email from From header: {from_header}"))
                            continue

                        phone = "Not provided"
                        product_name = subject[:200] if subject else "Email Inquiry"
                        product_description = (body or "Email inquiry")[:500]

                        # Try to parse structured lines like:
                        # Name = testing mail
                        # product name : testing mail
                        # mobile - 9981088145
                        # email : someone@example.com
                        # description : this is issue
                        if body:
                            for line in body.splitlines():
                                line_clean = line.strip()
                                lower = line_clean.lower()

                                # Name
                                if lower.startswith("name"):
                                    # split on = or :
                                    parts = re.split(r"[:=]", line_clean, 1)
                                    if len(parts) == 2:
                                        sender_name = parts[1].strip()

                                # Product name
                                elif "product" in lower and "name" in lower:
                                    parts = re.split(r"[:=]", line_clean, 1)
                                    if len(parts) == 2:
                                        pn = parts[1].strip()
                                        if pn:
                                            product_name = pn[:200]

                                # Mobile / phone
                                elif lower.startswith("mobile") or "phone" in lower:
                                    # extract number from the line
                                    phone_match = re.search(
                                        r"(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})",
                                        line_clean,
                                    )
                                    if phone_match:
                                        phone = phone_match.group(1)

                                # Email in body (only override if valid email found, not empty)
                                elif lower.startswith("email"):
                                    parts = re.split(r"[:=]", line_clean, 1)
                                    if len(parts) == 2:
                                        possible_email = parts[1].strip()
                                        # Only override sender email if a valid email is found in the body
                                        # If the line is empty (like "email : "), keep the From header email
                                        if possible_email:
                                            email_match = re.search(
                                                r"[\w\.-]+@[\w\.-]+\.\w+",
                                                possible_email,
                                            )
                                            if email_match:
                                                sender_addr = email_match.group(0)

                                # Description (single-line)
                                elif lower.startswith("description"):
                                    parts = re.split(r"[:=]", line_clean, 1)
                                    if len(parts) == 2:
                                        desc = parts[1].strip()
                                        if desc:
                                            product_description = desc[:500]

                        # If phone still not set and body has a number, fall back to full-body search
                        if phone == "Not provided" and body:
                            phone_match = re.search(
                                r"(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})",
                                body,
                            )
                            if phone_match:
                                phone = phone_match.group(1)

                        # Find or create lead, and always refresh details from the parsed body
                        from leads.models import Company
                        company_obj = None
                        if company_id:
                            company_obj = Company.objects.filter(id=company_id).first()
                        
                        lead, created = Lead.objects.get_or_create(
                            email=sender_addr,
                            company=company_obj,
                            defaults={
                                "name": sender_name or "Unknown",
                                "phone": phone,
                                "product_name": product_name,
                                "product_description": product_description,
                                "status": "inquiry",
                            },
                        )

                        if not created:
                            # Update lead fields with latest parsed values
                            lead.name = sender_name or lead.name
                            lead.phone = phone or lead.phone
                            lead.product_name = product_name or lead.product_name
                            lead.product_description = product_description or lead.product_description
                            if lead.status == "inquiry":
                                # keep status if already moved forward
                                lead.status = "inquiry"
                            lead.save()
                        else:
                            LeadActivity.objects.create(
                                lead=lead,
                                user=None,
                                action="Lead created from Gmail email",
                                details=f"Email received: {subject}",
                                new_status="inquiry",
                            )

                        # Check if ticket already exists for this email to prevent duplicates
                        ticket_subject = subject[:200] if subject else "Email Inquiry"
                        
                        # Check for existing ticket with same lead + subject + source
                        existing_ticket = Ticket.objects.filter(
                            lead=lead,
                            subject=ticket_subject,
                            source="email"
                        ).first()
                        
                        # Also check for tickets from same lead created recently (within 2 hours)
                        # This catches cases where subject might vary slightly
                        if not existing_ticket and email_date:
                            time_window_start = email_date - timedelta(hours=2)
                            time_window_end = email_date + timedelta(hours=2)
                            
                            recent_duplicate = Ticket.objects.filter(
                                lead=lead,
                                source="email",
                                created_at__gte=time_window_start,
                                created_at__lte=time_window_end,
                            ).first()
                            
                            if recent_duplicate:
                                existing_ticket = recent_duplicate
                        
                        if existing_ticket:
                            # Ticket already exists, skip creating duplicate
                            logger.info(f"Skipping duplicate ticket for email: {subject} from {sender_addr} (existing ticket #{existing_ticket.id})")
                            self.stdout.write(self.style.WARNING(f"Skipping duplicate: Ticket #{existing_ticket.id} already exists for this email"))
                            # Still mark email as seen to prevent reprocessing
                            mail.store(eid, "+FLAGS", "\\Seen")
                            continue

                        # Create new ticket only if it doesn't exist
                        ticket = Ticket.objects.create(
                            lead=lead,
                            subject=ticket_subject,
                            description=body or "No content",
                            customer_name=sender_name or lead.name,
                            customer_email=sender_addr,
                            customer_phone=phone,
                            status="open",
                            source="email",
                            company=company_obj,
                        )

                        LeadActivity.objects.create(
                            lead=lead,
                            user=None,
                            action=f"Ticket #{ticket.id} created from Gmail email",
                            details=f"Email subject: {subject}",
                            new_status=lead.status,
                        )

                        processed_count += 1

                        # Mark email as seen
                        mail.store(eid, "+FLAGS", "\\Seen")
                        
                        # Stop if we've reached the max
                        if processed_count >= max_to_process:
                            break
                    
                    # Stop if we've reached the max
                    if processed_count >= max_to_process:
                        break
                        
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Error processing folder {folder_name}: {e}"))
                    continue

            if total_found == 0:
                scope = "unseen" if unseen_only else "all"
                self.stdout.write(self.style.WARNING(f"No emails found in scope ({scope}) in INBOX or Spam."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Found {total_found} email(s) in scope; processed {processed_count} matching inquiry email(s) from Gmail."))

        finally:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

