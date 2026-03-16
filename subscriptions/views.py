from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from .models import Plan, CompanySubscription
from leads.models import Company, UserProfile
import datetime

def is_company_admin(user):
    return hasattr(user, 'userprofile') and user.userprofile.role == 'admin'

@login_required
@user_passes_test(is_company_admin)
def plan_list(request):
    plans = Plan.objects.filter(is_active=True).order_by('price')
    subscription = getattr(request.user.userprofile.company, 'subscription', None)
    
    return render(request, 'subscriptions/subscription_plans.html', {
        'plans': plans,
        'current_subscription': subscription,
        'days_remaining': subscription.days_remaining() if subscription else 0
    })

@login_required
@user_passes_test(is_company_admin)
def subscribe(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    company = request.user.userprofile.company
    
    # Calculate end date (assume monthly for now based on billing cycle)
    days = 30 if plan.billing_cycle == 'monthly' else 365
    end_date = timezone.now() + datetime.timedelta(days=days)
    
    subscription, created = CompanySubscription.objects.update_or_create(
        company=company,
        defaults={
            'plan': plan,
            'start_date': timezone.now(),
            'end_date': end_date,
            'status': 'active',
        }
    )
    
    messages.success(request, f"Successfully subscribed to {plan.name} plan.")
    return redirect('company_admin_dashboard')

@login_required
def renew_subscription(request):
    profile = request.user.userprofile
    if profile.role != 'admin':
        messages.error(request, "Only company admins can renew subscriptions.")
        return redirect('dashboard')
        
    plans = Plan.objects.filter(is_active=True).order_by('price')
    return render(request, 'subscriptions/subscription_renew.html', {'plans': plans})

def register_company(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        company_email = request.POST.get('company_email') # Not in model, maybe use as admin email?
        admin_name = request.POST.get('admin_name')
        admin_email = request.POST.get('admin_email')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        
        if User.objects.filter(username=admin_email).exists():
            messages.error(request, "User with this email already exists.")
            return render(request, 'subscriptions/register_company.html')
            
        # Create user
        user = User.objects.create_user(
            username=admin_email,
            email=admin_email,
            password=password,
            first_name=admin_name
        )
        
        # Create company
        company = Company.objects.create(
            name=company_name,
            admin=user,
            registration_type='self_registered'
        )
        
        # Update profile (already created by post_save signal)
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'company': company,
                'role': 'admin',
                'contact': phone
            }
        )
        
        from django.contrib.auth import login
        login(request, user)
        
        return redirect('subscriptions:plan_list')
        
    return render(request, 'subscriptions/register_company.html')
