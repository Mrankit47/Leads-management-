from django.core.management.base import BaseCommand
from subscriptions.models import Plan

class Command(BaseCommand):
    help = 'Create default subscription plans'

    def handle(self, *args, **kwargs):
        plans = [
            {
                'name': 'Free',
                'price': 0.00,
                'billing_cycle': 'monthly',
                'max_users': 2,
                'max_leads': 50,
                'description': 'Basic plan for small teams'
            },
            {
                'name': 'Starter',
                'price': 29.00,
                'billing_cycle': 'monthly',
                'max_users': 10,
                'max_leads': 500,
                'description': 'Ideal for growing startups'
            },
            {
                'name': 'Pro',
                'price': 79.00,
                'billing_cycle': 'monthly',
                'max_users': 50,
                'max_leads': 5000,
                'description': 'Advanced features for established companies'
            },
            {
                'name': 'Enterprise',
                'price': 199.00,
                'billing_cycle': 'monthly',
                'max_users': 1000,
                'max_leads': 100000,
                'description': 'Full scale solutions for large organizations'
            }
        ]

        for plan_data in plans:
            plan, created = Plan.objects.get_or_create(
                name=plan_data['name'],
                billing_cycle=plan_data['billing_cycle'],
                defaults={
                    'price': plan_data['price'],
                    'max_users': plan_data['max_users'],
                    'max_leads': plan_data['max_leads'],
                    'description': plan_data['description'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created plan "{plan.name}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Plan "{plan.name}" already exists'))
