from django.db import models
from django.contrib.auth.models import User
import uuid


class Company(models.Model):

    name = models.CharField(max_length=255)

    admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="company_admin"
    )

    is_active = models.BooleanField(default=True)
    registration_type = models.CharField(max_length=20, choices=(('internal', 'Internal'), ('self_registered', 'Self Registered')), default='internal')

    created_at = models.DateTimeField(auto_now_add=True)

    # Integration Settings
    whatsapp_instance_id = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_access_token = models.CharField(max_length=255, blank=True, null=True)
    gmail_email = models.EmailField(blank=True, null=True)
    gmail_app_password = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="departments")

    class Meta:
        unique_together = ('name', 'company')

    def __str__(self):
        return f"{self.name} ({self.company.name})"

class UserProfile(models.Model):

    ROLE_CHOICES = (
        ("superadmin", "Super Admin"),
        ("admin", "Admin"),
        ("manager", "Manager"),
        ("editor", "Editor"),
        ("hybrid", "Hybrid"),
        ("employee", "Employee"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    contact = models.CharField(max_length=20, blank=True)

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Lead(models.Model):

    STATUS_CHOICES = [
        ('inquiry', 'Inquiry'),
        ('running', 'Running'),
        ('proposal', 'Proposal'),
        ('negotiation', 'Negotiation'),
        ('complete', 'Complete'),
        ('closer', 'Closer'),
        ('invoice', 'Invoice'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]

    # Customer information
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    customer_company = models.CharField(max_length=200, blank=True)

    # Product inquiry
    product_name = models.CharField(max_length=200)
    product_description = models.TextField()

    # Lead management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inquiry')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')

    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.product_name} ({self.status})"


class LeadActivity(models.Model):

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    action = models.CharField(max_length=200)
    details = models.TextField(blank=True)

    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Lead Activities'

    def __str__(self):
        return f"{self.lead.name} - {self.action}"


class Ticket(models.Model):

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('running', 'Running'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
        ('inquiry', 'Inquiry'),
        ('proposal', 'Proposal'),
        ('negotiation', 'Negotiation'),
        ('closer', 'Closer'),
        ('invoice', 'Invoice'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]

    SOURCE_CHOICES = [
        ('web', 'Web Form'),
        ('chatbot', 'Chatbot'),
        ('email', 'Email'),
        ('manual', 'Manual'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('mid', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Public Ticket ID
    ticket_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        db_index=True
    )

    # Lead Relation
    lead = models.ForeignKey(
        "Lead",
        on_delete=models.CASCADE,
        related_name="tickets",
        null=True,
        blank=True
    )

    # Ticket Basic Info
    subject = models.CharField(max_length=200)
    description = models.TextField()

    # Customer Info
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)

    # Ticket Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open"
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="web"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="mid"
    )

    # Company Relation
    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tickets"
    )

    # Extra Fields
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    project = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    # Attachment
    attachment = models.FileField(
        upload_to="ticket_attachments/",
        blank=True,
        null=True
    )

    # Time Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):

        if not self.ticket_id:
            self.ticket_id = "TCK-" + str(uuid.uuid4().hex)[:6].upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_id} - {self.subject}"
    
class TicketActivity(models.Model):

    ticket = models.ForeignKey(
         Ticket,
         on_delete=models.CASCADE,
         related_name="activities"
     )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    action = models.CharField(max_length=255)

    message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket.ticket_id} - {self.action}"