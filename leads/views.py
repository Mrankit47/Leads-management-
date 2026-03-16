import json
import re

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.core.paginator import Paginator
from io import StringIO

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout

from .models import Lead, LeadActivity, Ticket, Company, UserProfile
from .forms import InquiryForm, LeadUpdateForm
from .models import TicketActivity


# ---------------- RBAC HELPERS ---------------- #

def is_superadmin(user):
    return hasattr(user, "userprofile") and user.userprofile.role == "superadmin"


def is_admin(user):
    return hasattr(user, "userprofile") and user.userprofile.role == "admin"


def is_manager(user):
    return hasattr(user, "userprofile") and user.userprofile.role == "manager"


def is_editor(user):
    return hasattr(user, "userprofile") and user.userprofile.role == "editor"


def is_hybrid(user):
    return hasattr(user, "userprofile") and user.userprofile.role == "hybrid"


def is_employee(user):
    return hasattr(user, "userprofile") and user.userprofile.role == "employee"


def is_sales_team(user):
    return hasattr(user, "userprofile") and user.userprofile.role in ["admin", "manager", "editor", "employee", "hybrid"]


# ---------------- PUBLIC INQUIRY FORM ---------------- #

def landing_page(request):
    return render(request, "leads/landing.html")

def inquiry_form(request):

    if request.method == "POST":

        form = InquiryForm(request.POST)

        if form.is_valid():

            lead = form.save(commit=False)
            lead.status = "inquiry"

            selected_company = form.cleaned_data['company']

            from subscriptions.services import check_lead_limit
            can_add_lead, lead_msg = check_lead_limit(selected_company)
            if not can_add_lead:
                messages.error(request, lead_msg)
                return redirect("inquiry_form")

            lead.company = selected_company
            lead.save()

            ticket = Ticket.objects.create(
                lead=lead,
                subject=lead.product_name,
                description=lead.product_description,
                customer_name=lead.name,
                customer_email=lead.email,
                customer_phone=lead.phone,
                status="open",
                source="web",
                company=selected_company,
            )

            LeadActivity.objects.create(
                lead=lead,
                user=None,
                action="Lead + Ticket created from web inquiry",
                new_status="inquiry",
            )

            messages.success(request, "Inquiry submitted successfully")
            return redirect("inquiry_form")

    else:
        form = InquiryForm()

    return render(request, "leads/inquiry_form.html", {"form": form})


# ---------------- PUBLIC CHATBOT SUBMIT ---------------- #

def chatbot_submit(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # The chatbot collects name, email, phone, company, product_name, message
            
            # For simplicity, if company name is provided, try to find one, else use a default or handle appropriately
            # Since landing page has no company context, we'll assign it to the first active company or superadmin logic
            # Let's try to map it to the first available company for generic inquiries if no specific company is selected
            company_obj = Company.objects.filter(is_active=True).first()
            if not company_obj:
                return JsonResponse({"ok": False, "error": "No active company found to assign this lead to."})

            from subscriptions.services import check_lead_limit
            can_add_lead, lead_msg = check_lead_limit(company_obj)
            if not can_add_lead:
                return JsonResponse({"ok": False, "error": "System limit reached. Cannot process inquiry."})

            lead = Lead.objects.create(
                name=data.get("name", "Unknown"),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                company_name_text=data.get("company", ""),
                product_name=data.get("product_name", "Chat Inquiry"),
                product_description=data.get("message", ""),
                status="inquiry",
                company=company_obj
            )

            ticket = Ticket.objects.create(
                lead=lead,
                subject=lead.product_name,
                description=lead.product_description,
                customer_name=lead.name,
                customer_email=lead.email,
                customer_phone=lead.phone,
                status="open",
                source="chatbot",
                company=company_obj,
            )

            LeadActivity.objects.create(
                lead=lead,
                user=None,
                action="Lead + Ticket created from chatbot",
                new_status="inquiry",
            )

            return JsonResponse({"ok": True, "ticket_id": ticket.id})
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)})

    return JsonResponse({"ok": False, "error": "Invalid request method."})

@login_required
@require_POST
def update_whatsapp_settings(request):
    profile = request.user.userprofile
    if profile.role not in ["admin", "manager"]:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)
    
    company = profile.company
    data = json.loads(request.body)
    
    company.whatsapp_instance_id = data.get("instance_id")
    company.whatsapp_access_token = data.get("access_token")
    company.save()
    
    return JsonResponse({"ok": True})

@login_required
@require_POST
def update_gmail_settings(request):
    profile = request.user.userprofile
    if profile.role not in ["admin", "manager"]:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)
    
    company = profile.company
    data = json.loads(request.body)
    
    company.gmail_email = data.get("email")
    company.gmail_app_password = data.get("app_password")
    company.save()
    
    return JsonResponse({"ok": True})


# ---------------- SUPERADMIN LOGIN ---------------- #

def superadmin_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password")
            return redirect("superadmin_login")

        if not hasattr(user, "userprofile"):
            messages.error(request, "User profile missing")
            return redirect("superadmin_login")

        if user.userprofile.role != "superadmin":
            messages.error(request, "You are not a superadmin")
            return redirect("superadmin_login")

        login(request, user)

        return redirect("superadmin_dashboard")

    return render(request, "leads/superadmin_login.html")


# ---------------- SUPERADMIN DASHBOARD ---------------- #

@login_required
@user_passes_test(is_superadmin)
def superadmin_dashboard(request):

    companies = Company.objects.all()

    company_data = []

    for company in companies:
        subscription = getattr(company, 'subscription', None)

        company_data.append({
            "company": company,
            "subscription": subscription,
            "days_remaining": subscription.days_remaining() if subscription else 0,
            "users_count": UserProfile.objects.filter(company=company).count(),
            "leads_count": Lead.objects.filter(company=company).count(),
        })

    context = {
        "company_data": company_data
    }

    return render(request, "leads/superadmin_dashboard.html", context)


# ---------------- CREATE COMPANY ---------------- #

@login_required
@user_passes_test(is_superadmin)
def create_company(request):

    if request.method == "POST":

        company_name = request.POST.get("company_name")
        admin_username = request.POST.get("admin_username")
        admin_email = request.POST.get("admin_email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Validation
        if not company_name or not admin_username or not admin_email or not password:
            messages.error(request, "All fields are required")
            return redirect("create_company")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("create_company")

        if Company.objects.filter(name=company_name).exists():
            messages.error(request, "Company already exists")
            return redirect("create_company")

        if User.objects.filter(username=admin_username).exists():
            messages.error(request, "Username already exists")
            return redirect("create_company")

        try:

            # Create Company Admin user
            admin_user = User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=password,
            )

            # Create Company
            company = Company.objects.create(
                name=company_name,
                admin=admin_user,
            )

            # Create or update UserProfile
            profile, created = UserProfile.objects.get_or_create(user=admin_user)

            profile.role = "admin"
            profile.company = company
            profile.save()

            messages.success(request, "Company created successfully")

            return redirect("superadmin_dashboard")

        except Exception as e:
            messages.error(request, f"Error creating company: {str(e)}")
            return redirect("create_company")

    return render(request, "leads/create_company.html")

@login_required
@user_passes_test(is_superadmin)
def delete_company(request, company_id):

    company = Company.objects.get(id=company_id)

    company.delete()

    messages.success(request,"Company deleted successfully")

    return redirect("superadmin_dashboard")

@login_required
@user_passes_test(is_admin)
def some_view(request):

    # Example of admin-only view
    return render(request, "leads/admin_only.html")

# ---------------- SALES DASHBOARD ---------------- #

@login_required
@user_passes_test(is_sales_team)
def dashboard(request):
    profile = request.user.userprofile
    company = profile.company

    # Get query params for filtering
    status_filter = request.GET.get("status")
    source_filter = request.GET.get("source")
    assigned_filter = request.GET.get("assigned")

    # Base Queryset
    tickets = Ticket.objects.select_related("lead", "lead__assigned_to").filter(company=company)

    # 1. Calculate General Leads Stats (regardless of filters)
    leads_queryset = Lead.objects.filter(company=company)
    stats = {
        "total": leads_queryset.count(),
        "inquiry": leads_queryset.filter(status="inquiry").count(),
        "proposal": leads_queryset.filter(status="proposal").count(),
        "negotiation": leads_queryset.filter(status="negotiation").count(),
        "closer": leads_queryset.filter(status="closer").count(),
        "invoice": leads_queryset.filter(status="invoice").count(),
    }

    # 2. Calculate Ticket Source Stats
    ticket_stats = {
        "total": Ticket.objects.filter(company=company).count(),
        "web": Ticket.objects.filter(company=company, source="web").count(),
        "chatbot": Ticket.objects.filter(company=company, source="chatbot").count(),
        "email": Ticket.objects.filter(company=company, source="email").count(),
    }

    # 3. Apply Filters to the listed tickets
    if status_filter:
        tickets = tickets.filter(lead__status=status_filter)
    
    if source_filter:
        tickets = tickets.filter(source=source_filter)
    
    if assigned_filter == "me":
        tickets = tickets.filter(lead__assigned_to=request.user)

    tickets = tickets.order_by("-created_at")

    # Pagination
    paginator = Paginator(tickets, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "leads/dashboard.html",
        {
            "tickets": page_obj,
            "status_filter": status_filter,
            "source_filter": source_filter,
            "assigned_filter": assigned_filter,
            "stats": stats,
            "ticket_stats": ticket_stats,
            "is_manager": is_manager(request.user),
            "company": company
        },
    )


# ---------------- LEAD DETAIL ---------------- #

@login_required
@user_passes_test(is_sales_team)
def lead_detail(request, lead_id):

    company = request.user.userprofile.company

    lead = get_object_or_404(
        Lead,
        id=lead_id,
        company=company,
    )

    activities = lead.activities.all()[:20]
    # Get associated ticket
    ticket = lead.tickets.first()

    if request.method == "POST":
        form = LeadUpdateForm(request.POST, instance=lead, company=company)
        
        # Handle ticket updates if ticket exists
        if ticket:
            priority = request.POST.get('priority')
            department = request.POST.get('department')
            project = request.POST.get('project')
            if priority: ticket.priority = priority
            if department: ticket.department = department
            if project: ticket.project = project
            ticket.save()

        if form.is_valid():
            old_status = lead.status
            updated_lead = form.save()

            if old_status != updated_lead.status:

                LeadActivity.objects.create(
                    lead=updated_lead,
                    user=request.user,
                    action=f"Status changed to {updated_lead.get_status_display()}",
                    old_status=old_status,
                    new_status=updated_lead.status,
                )

            messages.success(request, "Lead information updated successfully")

            return redirect("lead_detail", lead_id=lead.id)

    else:

        form = LeadUpdateForm(instance=lead, company=company)

    return render(
        request,
        "leads/lead_detail.html",
        {
            "lead": lead,
            "ticket": ticket,
            "form": form,
            "activities": activities,
        },
    )

@login_required
@user_passes_test(is_sales_team)
def delete_lead(request, lead_id):
    company = request.user.userprofile.company
    lead = get_object_or_404(Lead, id=lead_id, company=company)
    
    if request.method == "POST":
        lead.delete()
        messages.success(request, "Lead deleted successfully")
        return redirect("dashboard")
    
    return redirect("lead_detail", lead_id=lead_id)

# ---------------- MANAGER DASHBOARD ---------------- #

@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    profile = request.user.userprofile
    company = profile.company

    # Company Users (strictly excluding Admins, Superadmins, and the manager themselves)
    users = UserProfile.objects.filter(
        company=company
    ).exclude(role__in=["admin", "superadmin"]).exclude(user=request.user).select_related('user')

    # Available roles for managers to assign
    manageable_roles = [
        ("editor", "Editor"),
        ("hybrid", "Hybrid"),
        ("employee", "Employee"),
    ]

    context = {
        "company": company,
        "role": profile.role,
        "users_list": users,
        "manageable_roles": manageable_roles,
    }

    return render(
        request, 
        "leads/manager_dashboard.html", 
        context
    )

@login_required
@require_POST
def update_user_role(request):
    profile = request.user.userprofile
    if profile.role not in ["admin", "manager"]:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)
    
    data = json.loads(request.body)
    user_id = data.get("user_id")
    new_role = data.get("role")
    
    if new_role not in ["editor", "hybrid", "employee"]:
        return JsonResponse({"ok": False, "error": "Invalid role assignment"}, status=400)
    
    target_profile = get_object_or_404(UserProfile, user_id=user_id, company=profile.company)
    
    # Manager cannot change Admin/Superadmin roles even if they knew the ID
    if target_profile.role in ["admin", "superadmin"]:
        return JsonResponse({"ok": False, "error": "Cannot modify administrative roles"}, status=403)
        
    target_profile.role = new_role
    target_profile.save()
    
    return JsonResponse({"ok": True})

# ---------------- CHATBOT API ---------------- #

@csrf_exempt
@require_POST
def chatbot_submit(request):

    payload = json.loads(request.body.decode("utf-8"))

    company = Company.objects.first()

    from subscriptions.services import check_lead_limit
    can_add_lead, lead_msg = check_lead_limit(company)
    if not can_add_lead:
        return JsonResponse({"ok": False, "error": lead_msg}, status=403)

    lead = Lead.objects.create(
        name=payload.get("name"),
        email=payload.get("email"),
        phone=payload.get("phone"),
        product_name=payload.get("product_name"),
        product_description=payload.get("message"),
        status="inquiry",
        company=company,
    )

    ticket = Ticket.objects.create(
        lead=lead,
        subject=payload.get("product_name"),
        description=payload.get("message"),
        customer_name=payload.get("name"),
        customer_email=payload.get("email"),
        customer_phone=payload.get("phone"),
        status="open",
        source="chatbot",
        company=company,
    )

    LeadActivity.objects.create(
        lead=lead,
        user=None,
        action="Lead + Ticket created from chatbot",
        new_status="inquiry",
    )

    return JsonResponse(
        {
            "ok": True,
            "lead_id": lead.id,
            "ticket_id": ticket.id,
        }
    )


# ---------------- EMAIL FETCH ---------------- #

@login_required
@user_passes_test(is_manager)
@require_POST
def fetch_email_inquiries(request):

    out = StringIO()

    company = request.user.userprofile.company
    
    try:
        kwargs = {
            "max": 10,
            "unseen_only": True,
            "stdout": out,
        }
        
        # Pass company-specific credentials if they exist
        if company.gmail_email and company.gmail_app_password:
            kwargs["email"] = company.gmail_email
            kwargs["password"] = company.gmail_app_password
            kwargs["company_id"] = company.id

        call_command("fetch_gmail_inquiries", **kwargs)

        raw_output = out.getvalue()

        clean_output = re.sub(r"\x1b\[[0-9;]*m", "", raw_output or "")

        lines = [line.strip() for line in clean_output.splitlines() if line.strip()]

        summary = lines[-1] if lines else "Email extraction completed."

        messages.success(request, summary)

    except Exception as e:

        messages.error(request, f"Email extraction failed: {e}")

    finally:

        out.close()

    return redirect("manager_dashboard")

def user_logout(request):
    logout(request)
    return redirect("superadmin_login")


#--------------Employee Login & Dashboards----------------#

def employee_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check for superadmin role before logging in
            if hasattr(user, 'userprofile') and user.userprofile.role == "superadmin":
                messages.error(request, "Superadmins must use the SuperAdmin Login portal.")
                return redirect("login")

            login(request, user)

            role = user.userprofile.role

            if role == "admin":
                return redirect("company_admin_dashboard")
            elif role == "manager":
                return redirect("manager_dashboard")
            elif role in ["editor", "employee", "hybrid"]:
                return redirect("employee_dashboard")
            else:
                return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

    return render(request, "leads/login.html")

@login_required
@user_passes_test(is_admin)
def company_admin_dashboard(request):

    profile = request.user.userprofile
    company = profile.company

    # Stats
    users_count = UserProfile.objects.filter(company=company).count()
    leads_count = Lead.objects.filter(company=company).count()
    tickets_count = Ticket.objects.filter(company=company).count()

    # User list for dashboard
    users = UserProfile.objects.filter(company=company)

    subscription = getattr(company, 'subscription', None)
    days_remaining = subscription.days_remaining() if subscription else 0

    return render(
        request,
        "leads/company_admin_dashboard.html",
        {
            "company": company,
            "users_count": users_count,
            "leads_count": leads_count,
            "tickets_count": tickets_count,
            "users": users,
            "role": "Company Admin",
            "full_name": f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            "subscription": subscription,
            "days_remaining": days_remaining,
        },
    )

@login_required
def create_user(request):

    profile = request.user.userprofile
    company = profile.company

    # Security: Only Admin and Manager can create users
    if profile.role not in ["admin", "manager"]:
        messages.error(request, "Permission denied.")
        return redirect("users_list")

    if request.method == "POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        
        from subscriptions.services import check_user_limit
        can_create, message = check_user_limit(company)
        if not can_create:
            messages.error(request, message)
            return redirect("create_user")

        contact = request.POST.get("contact")
        department = request.POST.get("department")
        role = request.POST.get("role")   # ← IMPORTANT
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # password validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("create_user")

        # manager role restriction
        if profile.role == "manager":
            if role not in ["editor", "employee", "hybrid"]:
                messages.error(request, "Manager can only assign editor, employee or hybrid role")
                return redirect("create_user")

        # username validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("create_user")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Update profile (already created by post_save signal)
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'company': company,
                'role': role,
                'contact': contact,
                'department': department
            }
        )

        messages.success(request, "User created successfully")

        return redirect("users_list")

    return render(request, "leads/create_user.html", {"company": company})

@login_required
def users_list(request):

    profile = request.user.userprofile
    company = profile.company

    users = UserProfile.objects.filter(company=company)

    # Manager restrictions (already existed, keeping for safety)
    if profile.role == "manager":
        users = users.exclude(role="admin")

    # Editor/Employee/Hybrid restrictions
    if profile.role in ["editor", "employee", "hybrid"]:
        users = users.exclude(role__in=["admin", "manager"])

    return render(
        request,
        "leads/users_list.html",
        {
            "users": users,
            "role": profile.role.capitalize(),
            "company": company
        }
    )

@login_required
def delete_user(request, user_id):

    profile = request.user.userprofile

    # Security: Only Admin and Manager can delete users
    if profile.role not in ["admin", "manager"]:
        messages.error(request, "Permission denied.")
        return redirect("users_list")

    user = User.objects.get(id=user_id)

    if user.userprofile.company != profile.company:
        return redirect("users_list")

    user.delete()

    return redirect("users_list")

@login_required
def edit_user(request, user_id):

    profile = request.user.userprofile
    target_user = get_object_or_404(User, id=user_id)
    target_profile = target_user.userprofile

    # security check (same company)
    if target_profile.company != profile.company:
        messages.error(request, "Access denied.")
        return redirect("users_list")

    # Role-based restriction: Editor cannot edit Admin/Manager
    if profile.role == "editor" and target_profile.role in ["admin", "manager"]:
        messages.error(request, "Editors cannot edit Admin or Manager profiles.")
        return redirect("users_list")

    if request.method == "POST":
        # Both Admin and Editor can update these
        target_user.first_name = request.POST.get("first_name")
        target_user.last_name = request.POST.get("last_name")
        target_user.username = request.POST.get("username")
        target_user.email = request.POST.get("email")
        target_profile.contact = request.POST.get("contact")
        
        # Only Admin can update role and department (as per requirements for Editor)
        if profile.role == "admin":
            target_profile.department = request.POST.get("department")
            target_profile.role = request.POST.get("role")

        target_user.save()
        target_profile.save()
        
        messages.success(request, "User updated successfully.")
        return redirect("users_list")

    return render(
        request,
        "leads/edit_user.html",
        {
            "user_obj": target_user,
            "profile": target_profile,
            "is_admin": profile.role == "admin",
            "company": profile.company
        }
    )

# ---------------- CREATE TICKET ---------------- #

@login_required
def create_ticket(request):

    profile = request.user.userprofile
    company = profile.company

    users = User.objects.filter(
        userprofile__company=company
    )

    if request.method == "POST":

        subject = request.POST.get("subject")
        description = request.POST.get("description")
        priority = request.POST.get("priority")
        department = request.POST.get("department")
        project = request.POST.get("project")
        assigned_to = request.POST.get("assigned_to")

        assigned_user = None

        if assigned_to:
            assigned_user = User.objects.get(id=assigned_to)

        ticket = Ticket.objects.create(
            subject=subject,
            description=description,
            priority=priority,
            department=department,
            project=project,
            assigned_to=assigned_user,
            company=company,
            created_by=request.user,
            source="manual"
        )

        TicketActivity.objects.create(
            ticket=ticket,
            user=request.user,
            action="Ticket Created"
        )

        messages.success(request, "Ticket created successfully")

        return redirect("tickets_list")

    return render(
        request,
        "leads/create_ticket.html",
        {"users": users, "company": company}
    )


# ---------------- TICKET LIST ---------------- #

@login_required
def tickets_list(request):

    company = request.user.userprofile.company

    tickets = Ticket.objects.filter(
        company=company
    ).order_by("-created_at")

    return render(
        request,
        "leads/tickets_list.html",
        {"tickets": tickets, "company": company}
    )


# ---------------- TICKET DETAIL ---------------- #

@login_required
def ticket_detail(request, id):

    company = request.user.userprofile.company

    ticket = get_object_or_404(
        Ticket,
        id=id,
        company=company
    )

    activities = ticket.activities.all()

    return render(
        request,
        "leads/ticket_detail.html",
        {
            "ticket": ticket,
            "activities": activities,
            "company": company
        }
    )


# ---------------- DELETE TICKET ---------------- #

@login_required
def delete_ticket(request, id):

    company = request.user.userprofile.company

    ticket = get_object_or_404(
        Ticket,
        id=id,
        company=company
    )

    ticket.delete()

    messages.success(request, "Ticket deleted successfully")

    return redirect("tickets_list")

@login_required
@user_passes_test(is_superadmin)
def toggle_company_status(request, company_id):

    company = get_object_or_404(Company, id=company_id)

    company.is_active = not company.is_active

    company.save()

    if company.is_active:
        messages.success(request, "Company reactivated successfully")
    else:
        messages.warning(request, "Company access suspended")

    return redirect("superadmin_dashboard")

@login_required
@user_passes_test(is_superadmin)
def company_detail_view(request, company_id):

    company = get_object_or_404(Company, id=company_id)

    company_admin = company.admin

    users = UserProfile.objects.filter(company=company)

    leads = Lead.objects.filter(company=company).order_by("-created_at")

    tickets = Ticket.objects.filter(company=company).order_by("-created_at")

    context = {
        "company": company,
        "company_admin": company_admin,
        "users": users,
        "leads": leads,
        "tickets": tickets,
    }

    return render(
        request,
        "leads/company_detail.html",
        context
    )


# ---------------- ADMIN SALES DASHBOARD (Adashboard) ---------------- #

@login_required
@user_passes_test(is_admin)
def adashboard(request):

    company = request.user.userprofile.company

    leads = Lead.objects.filter(company=company)
    tickets = Ticket.objects.filter(company=company).select_related("lead").order_by("-created_at")

    stats = {
        "total": leads.count(),
        "inquiry": leads.filter(status="inquiry").count(),
        "proposal": leads.filter(status="proposal").count(),
        "negotiation": leads.filter(status="negotiation").count(),
        "closer": leads.filter(status="closer").count(),
        "invoice": leads.filter(status="invoice").count(),
    }

    ticket_stats = {
        "total": tickets.count(),
        "web": tickets.filter(source="web").count(),
        "chatbot": tickets.filter(source="chatbot").count(),
        "email": tickets.filter(source="email").count(),
    }

    context = {
        "stats": stats,
        "ticket_stats": ticket_stats,
        "tickets": tickets,
        "is_manager": False,
        "company": company,
    }

    return render(request, "leads/Adashboard.html", context)


# ---------------- MANAGER SALES DASHBOARD (Mdashboard) ---------------- #

@login_required
@user_passes_test(is_manager)
def mdashboard(request):

    company = request.user.userprofile.company

    leads = Lead.objects.filter(company=company)

    overall_stats = {
        "total_leads": leads.count(),
        "by_status": {
            "inquiry":     leads.filter(status="inquiry").count(),
            "proposal":    leads.filter(status="proposal").count(),
            "negotiation": leads.filter(status="negotiation").count(),
            "closer":      leads.filter(status="closer").count(),
            "invoice":     leads.filter(status="invoice").count(),
        },
        "unassigned": leads.filter(assigned_to__isnull=True).count(),
    }

    sales_team = User.objects.filter(userprofile__company=company).exclude(userprofile__role__in=["admin", "superadmin"])

    sales_stats = []
    for member in sales_team:
        member_leads = leads.filter(assigned_to=member)
        sales_stats.append({
            "user": member,
            "total_leads": member_leads.count(),
            "recent_activities": LeadActivity.objects.filter(
                lead__company=company, user=member
            ).count(),
            "by_status": {
                "inquiry":     member_leads.filter(status="inquiry").count(),
                "proposal":    member_leads.filter(status="proposal").count(),
                "negotiation": member_leads.filter(status="negotiation").count(),
                "closer":      member_leads.filter(status="closer").count(),
                "invoice":     member_leads.filter(status="invoice").count(),
            },
        })

    recent_activities = (
        LeadActivity.objects.filter(lead__company=company)
        .select_related("lead", "user")
        .order_by("-timestamp")[:50]
    )

    # Tickets for leads table
    tickets = (
        Ticket.objects.select_related("lead")
        .filter(company=company)
        .order_by("-created_at")
    )

    context = {
        "overall_stats": overall_stats,
        "sales_stats": sales_stats,
        "recent_activities": recent_activities,
        "tickets": tickets,
        "company": company,
    }

    return render(request, "leads/Mdashboard.html", context)

@login_required
def editor_dashboard(request):
    return redirect("employee_dashboard")

@login_required
def hybrid_dashboard(request):
    return redirect("employee_dashboard")

@login_required
def employee_dashboard(request):

    profile = request.user.userprofile
    company = profile.company
    role = profile.role.capitalize()

    # Assignment requirement: Employee/Hybrid/Editor should only see their assigned tickets
    if profile.role in ["editor", "hybrid", "employee"]:
        tickets = Ticket.objects.filter(company=company, assigned_to=request.user).order_by("-created_at")
    else:
        tickets = Ticket.objects.filter(company=company).order_by("-created_at")

    context = {
        "company": company,
        "tickets": tickets,
        "role": role,
        "full_name": f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        "user": request.user
    }

    return render(
        request,
        "leads/common_dashboard.html",
        context
    )

@login_required
def employee_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name")
        request.user.last_name = request.POST.get("last_name")
        request.user.email = request.POST.get("email")
        request.user.save()
        
        profile.contact = request.POST.get("contact")
        profile.save()
        
        messages.success(request, "Profile updated successfully.")
        return redirect("employee_profile")
        
    return render(request, "leads/profile.html", {
        "user": request.user,
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
        "profile": profile,
        "company": profile.company if profile.company else None,
        "full_name": f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    })

# ---------------- PUBLIC CHATBOT SUBMIT ---------------- #

@csrf_exempt
def chatbot_submit(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # The chatbot collects name, email, phone, company, product_name, message
            
            # Since landing page has no company context, assign it to the first active company
            # We filter generically for active companies to ensure this runs out-of-the-box
            company_obj = Company.objects.filter(is_active=True).first()
            if not company_obj:
                return JsonResponse({"ok": False, "error": "No active company found to assign this lead to."})

            from subscriptions.services import check_lead_limit
            can_add_lead, lead_msg = check_lead_limit(company_obj)
            if not can_add_lead:
                return JsonResponse({"ok": False, "error": "System limit reached. Cannot process inquiry."})

            # Create lead
            lead = Lead.objects.create(
                name=data.get("name", "Unknown"),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                company_name_text=data.get("company", ""),
                product_name=data.get("product_name", "Chat Inquiry"),
                product_description=data.get("message", ""),
                status="inquiry",
                company=company_obj
            )

            # Create ticket representing the chatbot inquiry
            ticket = Ticket.objects.create(
                lead=lead,
                subject=lead.product_name,
                description=lead.product_description,
                customer_name=lead.name,
                customer_email=lead.email,
                customer_phone=lead.phone,
                status="open",
                source="chatbot",
                company=company_obj,
            )

            # Log activity automatically
            LeadActivity.objects.create(
                lead=lead,
                user=None,
                action="Lead + Ticket created from chatbot",
                new_status="inquiry",
            )

            return JsonResponse({"ok": True, "ticket_id": ticket.id})
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)})

    return JsonResponse({"ok": False, "error": "Invalid request method."})