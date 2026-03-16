from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from .models import CompanySubscription
from leads.models import UserProfile

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Skip checks for admin and superadmin (Django Admin)
        if request.path.startswith('/admin/') or request.path.startswith('/logout/'):
            return self.get_response(request)

        # Get UserProfile
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            return self.get_response(request)

        # Superadmins skip all subscription checks
        if profile.role == 'superadmin':
            return self.get_response(request)

        # Company scope
        company = profile.company
        if not company:
            return self.get_response(request)

        subscription = getattr(company, 'subscription', None)

        # Paths to exempt from redirection
        exempt_paths = [
            reverse('subscriptions:plan_list'),
            reverse('subscriptions:renew'),
            # reverse('leads:logout'), # Handled above via string check
        ]

        if request.path in exempt_paths:
            return self.get_response(request)

        # 1. No subscription - DO NOT redirect automatically as per refined requirement
        if not subscription:
            return self.get_response(request)

        # 2. Expired subscription - Redirect to renew
        if not subscription.is_active():
            return redirect('subscriptions:renew')

        return self.get_response(request)
