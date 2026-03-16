from django.contrib import messages
from leads.models import UserProfile, Lead

def check_user_limit(company):
    subscription = getattr(company, 'subscription', None)
    if not subscription:
        return True, "" # Or block if required

    max_users = subscription.plan.max_users
    current_users = UserProfile.objects.filter(company=company).count()

    if current_users >= max_users:
        return False, "Your plan limit for users has been reached. Upgrade your plan."
    
    return True, ""

def check_lead_limit(company):
    subscription = getattr(company, 'subscription', None)
    if not subscription:
        return True, ""

    max_leads = subscription.plan.max_leads
    current_leads = Lead.objects.filter(company=company).count()

    if current_leads >= max_leads:
        return False, "Your plan limit for leads has been reached. Upgrade your plan."
    
    return True, ""

from django.core.mail import send_mail
from django.conf import settings

def send_expiry_notification(subscription):
    subject = f"Your LeadGen Tracker subscription for {subscription.company.name} is expiring soon"
    message = f"Hello {subscription.company.admin.first_name},\n\nYour {subscription.plan.name} subscription will expire in {subscription.days_remaining()} days. Please renew or upgrade to avoid service interruption.\n\nBest regards,\nLeadGen Tracker Team"
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [subscription.company.admin.email],
        fail_silently=True,
    )
