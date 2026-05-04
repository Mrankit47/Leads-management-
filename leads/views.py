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

from django.contrib.auth import authenticate, login, logout, get_user_model
User = get_user_model()
from subscriptions.services import check_lead_limit, check_user_limit
from subscriptions.services import check_user_limit
from leads.models import Lead, LeadActivity, Ticket, Company, UserProfile, TicketActivity, Department
from leads.forms import InquiryForm, LeadUpdateForm


def get_dashboard_url(user):
    """Returns the named URL for the user's primary dashboard based on their role."""
    profile = getattr(user, 'userprofile', None)
    role = str(getattr(profile, 'role', '')).lower() if profile else None

    if user.is_superuser:
        return 'superadmin_dashboard'
    if role == 'admin':
        return 'company_admin_dashboard'
    if role == 'manager':
        return 'manager_dashboard'
    if role in ['editor', 'hybrid', 'employee']:
        return 'employee_dashboard'
    return 'home'


# ---------------- RBAC HELPERS ---------------- #

def is_superadmin(user):
    """Check if user has superadmin role"""
    if not user or not user.is_authenticated: return False
    profile = getattr(user, 'userprofile', None)
    return profile is not None and str(profile.role).lower() == "superadmin"

def is_admin(user):
    """Check if user has admin role"""
    if not user or not user.is_authenticated: return False
    profile = getattr(user, 'userprofile', None)
    return profile is not None and str(profile.role).lower() == "admin"

def is_manager(user):
    """Check if user has manager role"""
    if not user or not user.is_authenticated: return False
    profile = getattr(user, 'userprofile', None)
    return profile is not None and str(profile.role).lower() == "manager"

def is_editor(user):
    """Check if user has editor role"""
    if not user or not user.is_authenticated: return False
    profile = getattr(user, 'userprofile', None)
    return profile is not None and str(profile.role).lower() == "editor"

def is_hybrid(user):
    """Check if user has hybrid role"""
    if not user or not user.is_authenticated: return False
    profile = getattr(user, 'userprofile', None)
    return profile is not None and str(profile.role).lower() == "hybrid"

def is_employee(user):
    """Check if user has employee role"""
    if not user or not user.is_authenticated: return False
    profile = getattr(user, 'userprofile', None)
    return profile is not None and str(profile.role).lower() == "employee"

def is_sales_team(user):
    """Check if user belongs to any sales/management role"""
    if not user or not user.is_authenticated: return False
    profile = getattr(user, 'userprofile', None)
    if not profile: return False
    role = str(profile.role).lower()
    return role in ["admin", "manager", "editor", "employee", "hybrid"]


# ---------------- PUBLIC INQUIRY FORM ---------------- #

def landing_page(request):
    """Public landing page. Redirects authenticated users to the dashboard."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "leads/landing.html")

def inquiry_form(request):

    if request.method == "POST":

        form = InquiryForm(request.POST)

        if form.is_valid():

            lead = form.save(commit=False)
            lead.status = "inquiry"

            selected_company = form.cleaned_data['company']

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

@csrf_exempt
@require_POST
def chatbot_submit(request):
    """
    Public API endpoint for the chatbot to submit inquiries.
    Automatically creates a Lead and a corresponding Ticket for the first active company.
    """
    try:
        data = json.loads(request.body)
        
        # Assign to the first active company in the system
        company_obj = Company.objects.filter(is_active=True).first()
        if not company_obj:
            return JsonResponse({"ok": False, "error": "No active company found."}, status=404)

        # Check lead limits for the subscription
        can_add_lead, lead_msg = check_lead_limit(company_obj)
        if not can_add_lead:
            return JsonResponse({"ok": False, "error": lead_msg}, status=403)

        # Create the lead
        lead = Lead.objects.create(
            name=data.get("name", "Unknown"),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            customer_company=data.get("company", ""),
            product_name=data.get("product_name", "Chat Inquiry"),
            product_description=data.get("message", ""),
            status="inquiry",
            company=company_obj
        )

        # Create the ticket
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

        # Log the activity
        LeadActivity.objects.create(
            lead=lead,
            user=None,
            action="Lead + Ticket created from chatbot",
            new_status="inquiry",
        )

        return JsonResponse({"ok": True, "ticket_id": ticket.id, "lead_id": lead.id})

    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@login_required
@require_POST
def update_whatsapp_settings(request):
    profile = getattr(request.user, 'userprofile', None)
    if getattr(profile, 'role', None) not in ["admin", "manager"]:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)
    
    company = getattr(profile, 'company', None) if profile else None
    if not company:
        return JsonResponse({"ok": False, "error": "Company not found"}, status=404)
        
    data = json.loads(request.body)
    
    company.whatsapp_instance_id = data.get("instance_id")
    company.whatsapp_access_token = data.get("access_token")
    company.save()
    
    return JsonResponse({"ok": True})

@login_required
@require_POST
def update_gmail_settings(request):
    profile = getattr(request.user, 'userprofile', None)
    if getattr(profile, 'role', None) not in ["admin", "manager"]:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)
    
    company = getattr(profile, 'company', None) if profile else None
    if not company:
        return JsonResponse({"ok": False, "error": "Company not found"}, status=404)
        
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

        if not user.is_active:
            messages.error(request, "This account is inactive.")
            return redirect("superadmin_login")

        profile = getattr(user, 'userprofile', None)
        role = str(getattr(profile, 'role', '')).lower()
        if role != "superadmin":
            messages.error(request, "You do not have superadmin privileges.")
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
            if profile:
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
    profile = getattr(request.user, 'userprofile', None)
    company = (profile.company if profile else None)

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

    # Set Dashboard Context for Managers
    if profile and str(getattr(profile, 'role', '')).lower() == "manager":
        request.session['dashboard_context'] = 'secondary'

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
            "company": company,
            "dashboard_url": get_dashboard_url(request.user)
        },
    )


# ---------------- LEAD DETAIL ---------------- #



@login_required
@user_passes_test(is_sales_team)
def lead_detail(request, lead_id):
    """Detailed view for a single lead"""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

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
        
        # Extract ticket fields
        if ticket:
            priority = request.POST.get('priority')
            department = request.POST.get('department')
            project = request.POST.get('project')
            if priority: ticket.priority = priority
            if department: ticket.department = department
            if project: ticket.project = project

        if form.is_valid():
            old_status = lead.status
            old_assigned_to = lead.assigned_to
            updated_lead = form.save()
            
            # Sync to Ticket
            if ticket:
                ticket.status = updated_lead.status
                ticket.assigned_to = updated_lead.assigned_to
                ticket.save()

            # Log Status Change
            if old_status != updated_lead.status:
                LeadActivity.objects.create(
                    lead=updated_lead,
                    user=request.user,
                    action=f"Status changed to {updated_lead.get_status_display()}",
                    old_status=old_status,
                    new_status=updated_lead.status,
                )
            
            # Log Reassignment Change
            if old_assigned_to != updated_lead.assigned_to:
                assignee_name = updated_lead.assigned_to.get_full_name() or updated_lead.assigned_to.username if updated_lead.assigned_to else "Unassigned"
                LeadActivity.objects.create(
                    lead=updated_lead,
                    user=request.user,
                    action=f"Lead reassigned to {assignee_name}",
                    old_status=updated_lead.status,
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
    """Deletes a specific lead."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None
 
    if not company:
        messages.error(request, "User profile or company not found.")
        return redirect("dashboard")

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
    """Displays the manager dashboard with company users and roles."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None
 
    if not profile or not company:
        messages.error(request, "User profile or company not found.")
        return redirect("login")

    # Company Users (strictly excluding Admins, Superadmins, and the manager themselves)
    users = UserProfile.objects.filter(
        company=company
    ).exclude(role__iexact="admin").exclude(role__iexact="superadmin").exclude(user=request.user).select_related('user')

    # Available roles for managers to assign
    manageable_roles = [
        ("editor", "Editor"),
        ("employee", "Employee"),
    ]

    context = {
        "company": company,
        "role": getattr(profile, 'role', None),
        "users_list": users,
        "manageable_roles": manageable_roles,
    }

    # Set Dashboard Context for Managers
    request.session['dashboard_context'] = 'main'

    return render(
        request, 
        "leads/manager_dashboard.html", 
        context
    )

@login_required
@require_POST
def update_user_role(request):
    """Updates the role of a user within the company via AJAX."""
    profile = getattr(request.user, 'userprofile', None)
    if not profile:
        return JsonResponse({"ok": False, "error": "User profile not found"}, status=403)

    role = str(getattr(profile, 'role', '')).lower()
    if role not in ["admin", "manager"]:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)
    
    data = json.loads(request.body)
    user_id = data.get("user_id")
    new_role = data.get("role")
    
    if new_role not in ["editor", "hybrid", "employee"]:
        return JsonResponse({"ok": False, "error": "Invalid role assignment"}, status=400)
    
    company = getattr(profile, 'company', None) if profile else None
    target_profile = get_object_or_404(UserProfile, user_id=user_id, company=company)
    
    # Manager cannot change Admin/Superadmin roles even if they knew the ID
    if str(target_profile.role).lower() in ["admin", "superadmin"]:
        return JsonResponse({"ok": False, "error": "Cannot modify administrative roles"}, status=403)
        
    target_profile.role = new_role
    target_profile.save()
    
    return JsonResponse({"ok": True})

# ---------------- CHATBOT API ---------------- #



# ---------------- EMAIL FETCH ---------------- #

@login_required
@user_passes_test(is_manager)
@require_POST
def fetch_email_inquiries(request):
    """Fetches email inquiries for the company using a management command."""
    out = StringIO()

    profile = getattr(request.user, 'userprofile', None)
    company = (profile.company if profile else None) if profile else None

    if not company:
        messages.error(request, "User profile or company not found.")
        return redirect("some_error_page") # Or a more appropriate redirect
    
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
    """Logs out the current user and redirects to the superadmin login page."""
    logout(request)
    return redirect("superadmin_login")


#--------------Employee Login & Dashboards----------------#

def employee_login(request):
    """Handles employee login and redirects based on user role."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "This account is inactive.")
                return redirect("login")

            profile = getattr(user, 'userprofile', None)
            if not profile:
                messages.error(request, "User profile not found. Please contact your admin.")
                return redirect("login")

            role = str(getattr(profile, 'role', '')).lower()
            
            if role == "superadmin":
                messages.error(request, "Superadmins must use the SuperAdmin Login portal.")
                return redirect("login")

            login(request, user)

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
    """Displays the company admin dashboard with company statistics and user list."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not profile or not company:
        messages.error(request, "User profile or company not found.")
        return redirect("login") # Or a more appropriate redirect

    # Stats
    users_count = UserProfile.objects.filter(company=company).count()
    leads_count = Lead.objects.filter(company=company).count()
    tickets_count = Ticket.objects.filter(company=company).count()

    # User list for dashboard
    users = UserProfile.objects.filter(company=company)

    subscription = getattr(company, 'subscription', None)
    days_remaining = subscription.days_remaining() if subscription else 0

    full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username

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
            "full_name": full_name,
            "subscription": subscription,
            "days_remaining": days_remaining,
        },
    )

@login_required
def create_user(request):
    """Handles the creation of new users within a company."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not profile or not company:
        messages.error(request, "User profile or company not found.")
        return redirect("login") # Or a more appropriate redirect

    # Security: Only Admin and Manager can create users
    if getattr(profile, 'role', None) not in ["admin", "manager"]:
        messages.error(request, "Permission denied.")
        return redirect("users_list")

    if request.method == "POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        
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

        role_lower = str(role).lower()
        profile_role = str(getattr(profile, 'role', '')).lower()
        if profile_role == "admin":
            if role_lower in ["admin", "hybrid", "superadmin"]:
                messages.error(request, f"Cannot assign {role} role.")
                return redirect("create_user")
        
        # manager role restriction
        if profile_role == "manager":
            if role_lower not in ["editor", "employee"]: # Removed hybrid
                messages.error(request, "Manager can only assign editor or employee role")
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

        # Fetch Department object
        dept_obj = None
        if department:
            try:
                dept_obj = Department.objects.get(id=department, company=company)
            except (Department.DoesNotExist, ValueError):
                pass

        # Update profile (already created by post_save signal)
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'company': company,
                'role': role,
                'contact': contact,
                'department': dept_obj
            }
        )

        messages.success(request, "User created successfully")

        return redirect("users_list")

    # Role filtering for dropdown
    all_roles = UserProfile.ROLE_CHOICES
    profile_role = str(getattr(profile, 'role', '')).lower()
    if profile_role == "admin":
        assignable_roles = [r for r in all_roles if r[0] not in ["admin", "hybrid", "superadmin"]]
    elif profile_role == "manager":
        assignable_roles = [r for r in all_roles if r[0] in ["editor", "employee"]]
    else:
        assignable_roles = []

    available_departments = Department.objects.filter(company=company)

    return render(request, "leads/create_user.html", {
        "company": company,
        "assignable_roles": assignable_roles,
        "available_departments": available_departments
    })

@login_required
def users_list(request):
    """Displays a list of users within the current user's company, with role-based filtering."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not profile or not company:
        messages.error(request, "User profile or company not found.")
        return redirect("login") # Or a more appropriate redirect

    users = UserProfile.objects.filter(company=company)

    # Role-based visibility logic
    role = str(getattr(profile, 'role', '')).lower()
    if role == "editor":
        # Editors see everyone in their company EXCEPT Admins
        users = users.exclude(role__iexact="admin")
    elif role in ["employee", "hybrid"]:
        # Standard employees/hybrids see only other employees/editors/hybrids
        users = users.exclude(role__iexact="admin").exclude(role__iexact="manager")
    elif role == "manager":
        # Managers see everyone EXCEPT Admins
        users = users.exclude(role__iexact="admin")

    return render(
        request,
        "leads/users_list.html",
        {
            "users": users,
            "role": str(getattr(profile, 'role', None)).capitalize(),
            "company": company
        }
    )

@login_required
def delete_user(request, user_id):
    """Deletes a user from the company."""
    profile = getattr(request.user, 'userprofile', None)

    if not profile:
        messages.error(request, "User profile not found.")
        return redirect("some_error_page") # Or a more appropriate redirect

    # Security: Only Admin and Manager can delete users
    if getattr(profile, 'role', None) not in ["admin", "manager"]:
        messages.error(request, "Permission denied.")
        return redirect("users_list")

    user = User.objects.get(id=user_id)
    target_profile = getattr(user, 'userprofile', None)

    if not target_profile or target_profile.company != getattr(profile, 'company', None):
        messages.error(request, "Access denied or target user profile not found.")
        return redirect("users_list")

    user.delete()

    return redirect("users_list")

@login_required
def edit_user(request, user_id):
    """Handles editing of a user's profile within the company."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not profile or not company:
        messages.error(request, "User profile or company not found.")
        return redirect("login") # Or a more appropriate redirect

    target_user = get_object_or_404(User, id=user_id)
    target_profile = getattr(target_user, 'userprofile', None)
 
    if not target_profile:
        messages.error(request, "Target user profile not found.")
        return redirect("users_list")
 
    # security check (same company)
    if target_profile.company != company:
        messages.error(request, "Access denied.")
        return redirect("users_list")


    # Role-based restriction: Editor cannot edit Admin/Manager
    role = str(getattr(profile, 'role', '')).lower()
    target_role = str(getattr(target_profile, 'role', '')).lower()
    if role == "editor" and target_role in ["admin", "manager"]:
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
        if str(getattr(profile, 'role', '')).lower() == "admin":
            if target_profile:
                # Fetch Department object
                new_dept_id = request.POST.get("department")
                new_role = request.POST.get("role")
                
                if new_dept_id:
                    try:
                        target_profile.department = Department.objects.get(id=new_dept_id, company=company)
                    except (Department.DoesNotExist, ValueError):
                        pass
                
                # Role validation (prevent assigning admin/hybrid)
                if str(new_role).lower() not in ["admin", "hybrid", "superadmin"]:
                    target_profile.role = new_role
                
                target_profile.save()
        
        messages.success(request, "User updated successfully.")
        return redirect("users_list")
 
    # Role filtering for dropdown
    all_roles = UserProfile.ROLE_CHOICES
    assignable_roles = [r for r in all_roles if r[0] not in ["admin", "hybrid", "superadmin"]]
    available_departments = Department.objects.filter(company=company)

    return render(
        request,
        "leads/edit_user.html",
        {
            "user_obj": target_user,
            "profile": target_profile,
            "company": company,
            "is_admin": getattr(profile, 'role', None) == "admin",
            "assignable_roles": assignable_roles,
            "available_departments": available_departments
        }
    )

# ---------------- CREATE TICKET ---------------- #

@login_required
def create_ticket(request):
    """Handles the creation of a new support ticket."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None
 
    if not profile or not company:
        messages.error(request, "User profile or company not found.")
        return redirect("login")

    users = User.objects.filter(
        userprofile__company=company
    ).exclude(userprofile__role__iexact='admin')

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

    # Determine Dashboard URL for Back Link
    dashboard_url = get_dashboard_url(request.user)

    return render(
        request,
        "leads/create_ticket.html",
        {"users": users, "company": company, "dashboard_url": dashboard_url}
    )


@login_required
def edit_ticket(request, id):
    """Handles updating an existing support ticket."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None
 
    if not profile or not company:
        messages.error(request, "User profile or company not found.")
        return redirect("login")

    ticket = get_object_or_404(Ticket, id=id, company=company)
    
    # Ownership Check: Only assignee or admin can edit
    if ticket.assigned_to != request.user and str(getattr(profile, 'role', '')).lower() != 'admin':
        messages.error(request, "Permission denied. You can only edit tickets assigned to you.")
        return redirect("ticket_detail", id=ticket.id)

    # Assignment filtering: exclude admins
    users = User.objects.filter(userprofile__company=company).exclude(userprofile__role__iexact='admin')

    if request.method == "POST":
        subject = request.POST.get("subject")
        description = request.POST.get("description")
        priority = request.POST.get("priority")
        department = request.POST.get("department")
        project = request.POST.get("project")
        assigned_to = request.POST.get("assigned_to")
        status = request.POST.get("status")

        assigned_user = None
        if assigned_to:
            try:
                assigned_user = User.objects.get(id=assigned_to)
            except User.DoesNotExist:
                pass

        # Track changes for activity
        changes = []
        if ticket.subject != subject: changes.append(f"Subject changed")
        if ticket.status != status: changes.append(f"Status: {ticket.status} -> {status}")
        if ticket.assigned_to != assigned_user: 
            old_name = ticket.assigned_to.username if ticket.assigned_to else "Unassigned"
            new_name = assigned_user.username if assigned_user else "Unassigned"
            changes.append(f"Assigned: {old_name} -> {new_name}")

        ticket.subject = subject
        ticket.description = description
        ticket.priority = priority
        ticket.department = department
        ticket.project = project
        ticket.assigned_to = assigned_user
        ticket.status = status
        ticket.save()

        if changes:
            TicketActivity.objects.create(
                ticket=ticket,
                user=request.user,
                action=", ".join(changes) if len(", ".join(changes)) < 200 else "Ticket Updated"
            )

        messages.success(request, "Ticket updated successfully.")
        return redirect("ticket_detail", id=ticket.id)

    return render(
        request,
        "leads/edit_ticket.html",
        {
            "ticket": ticket,
            "users": users,
            "company": company,
            "dashboard_url": get_dashboard_url(request.user),
            "status_choices": Ticket.STATUS_CHOICES,
            "priority_choices": Ticket.PRIORITY_CHOICES,
        }
    )


# ---------------- TICKET LIST ---------------- #

@login_required
def tickets_list(request):
    """Displays a list of all tickets for the current user's company."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not company:
        messages.error(request, "User profile or company not found.")
        return redirect("some_error_page") # Or a more appropriate redirect

    tickets = Ticket.objects.filter(
        company=company
    ).order_by("-created_at")

    # Determine Dashboard URL for Back Link
    dashboard_url = get_dashboard_url(request.user)

    return render(
        request,
        "leads/tickets_list.html",
        {"tickets": tickets, "company": company, "dashboard_url": dashboard_url}
    )


# ---------------- TICKET DETAIL ---------------- #

@login_required
def ticket_detail(request, id):
    """Displays the details of a specific ticket."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not company:
        messages.error(request, "User profile or company not found.")
        return redirect("some_error_page") # Or a more appropriate redirect

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
            "company": company,
            "dashboard_url": get_dashboard_url(request.user)
        }
    )


# ---------------- DELETE TICKET ---------------- #

@login_required
def delete_ticket(request, id):
    """Deletes a specific ticket."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not company:
        messages.error(request, "User profile or company not found.")
        return redirect("some_error_page") # Or a more appropriate redirect

    ticket = get_object_or_404(
        Ticket,
        id=id,
        company=company
    )

    # Ownership Check: Only assignee or admin can delete
    if ticket.assigned_to != request.user and str(getattr(profile, 'role', '')).lower() != 'admin':
        messages.error(request, "Permission denied. You can only delete tickets assigned to you.")
        return redirect("ticket_detail", id=ticket.id)

    ticket.delete()

    messages.success(request, "Ticket deleted successfully")

    return redirect("tickets_list")

@login_required
@user_passes_test(is_superadmin)
def toggle_company_status(request, company_id):
    """Toggles the active status of a company (activate/deactivate)."""
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
    """Displays detailed information about a specific company for superadmins."""
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
    """Displays the admin sales dashboard with company-wide lead and ticket statistics."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not company:
        messages.error(request, "User profile or company not found.")
        return redirect("some_error_page") # Or a more appropriate redirect

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
    """Displays the manager sales dashboard with overall and per-sales-team member statistics."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None

    if not company:
        messages.error(request, "User profile or company not found.")
        return redirect("some_error_page") # Or a more appropriate redirect

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

    # Set Dashboard Context for Managers
    request.session['dashboard_context'] = 'main'

    return render(request, "leads/Mdashboard.html", context)

@login_required
def editor_dashboard(request):
    """Redirects editor users to the common employee dashboard."""
    return redirect("employee_dashboard")

@login_required
def hybrid_dashboard(request):
    """Redirects hybrid users to the common employee dashboard."""
    return redirect("employee_dashboard")
@login_required
def employee_dashboard(request):
    """Displays a common dashboard for employee, hybrid, and editor roles."""
    profile = getattr(request.user, 'userprofile', None)
    company = getattr(profile, 'company', None) if profile else None
 
    if not profile or not company:
        messages.error(request, "User profile or company not found.")
        return redirect("login")
 
    role = str(getattr(profile, 'role', None)).capitalize()


    # Assignment requirement: Employee/Hybrid/Editor should only see their assigned tickets
    role_lower = str(getattr(profile, 'role', '')).lower()
    if role_lower in ["editor", "hybrid", "employee"]:
        tickets = Ticket.objects.filter(company=company, assigned_to=request.user).order_by("-created_at")
    else:
        tickets = Ticket.objects.filter(company=company).order_by("-created_at")

    # Fetch users for Editor role (same as users_list logic)
    users = UserProfile.objects.none()
    if role_lower == "editor":
        users = UserProfile.objects.filter(company=company).exclude(role__iexact="admin")

    context = {
        "company": company,
        "tickets": tickets,
        "users": users,
        "role": role,
        "full_name": f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        "user": request.user
    }

    # Set Dashboard Context for Managers
    if profile and str(getattr(profile, 'role', '')).lower() == "manager":
        request.session['dashboard_context'] = 'secondary'

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
        
    full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username

    # Determine Dashboard URL for Back Link
    dashboard_url = 'employee_dashboard'
    role_lower = str(getattr(profile, 'role', '')).lower()
    if role_lower == "manager":
        context_type = request.session.get('dashboard_context', 'main')
        dashboard_url = 'manager_dashboard' if context_type == 'main' else 'employee_dashboard'
    elif role_lower == 'admin':
        dashboard_url = 'company_admin_dashboard'
    elif request.user.is_superuser:
        dashboard_url = 'superadmin_dashboard'

    return render(request, "leads/profile.html", {
        "user": request.user,
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
        "profile": profile,
        "company": (profile.company if profile else None) if (profile.company if profile else None) else None,
        "full_name": full_name,
        "dashboard_url": dashboard_url
    })
