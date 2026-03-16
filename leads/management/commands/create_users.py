from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = 'Creates synthetic accounts for sales team and manager'

    def handle(self, *args, **options):
        # Create Manager group
        manager_group, created = Group.objects.get_or_create(name='Manager')
        if created:
            self.stdout.write(self.style.SUCCESS('Created Manager group'))
        
        # Create Sales Team group
        sales_group, created = Group.objects.get_or_create(name='Sales Team')
        if created:
            self.stdout.write(self.style.SUCCESS('Created Sales Team group'))
        
        # Create Manager account
        manager, created = User.objects.get_or_create(
            username='manager',
            defaults={
                'email': 'manager@company.com',
                'first_name': 'John',
                'last_name': 'Manager',
                'is_staff': True,
            }
        )
        if created:
            manager.set_password('manager123')
            manager.save()
            manager.groups.add(manager_group)
            self.stdout.write(self.style.SUCCESS('Created manager account (username: manager, password: manager123)'))
        else:
            self.stdout.write(self.style.WARNING('Manager account already exists'))
        
        # Create Sales Team accounts
        sales_team_members = [
            {'username': 'sales1', 'email': 'sales1@company.com', 'first_name': 'Alice', 'last_name': 'Smith'},
            {'username': 'sales2', 'email': 'sales2@company.com', 'first_name': 'Bob', 'last_name': 'Johnson'},
            {'username': 'sales3', 'email': 'sales3@company.com', 'first_name': 'Carol', 'last_name': 'Williams'},
        ]
        
        for member in sales_team_members:
            user, created = User.objects.get_or_create(
                username=member['username'],
                defaults={
                    'email': member['email'],
                    'first_name': member['first_name'],
                    'last_name': member['last_name'],
                }
            )
            if created:
                user.set_password('sales123')
                user.save()
                user.groups.add(sales_group)
                self.stdout.write(self.style.SUCCESS(f"Created sales account: {member['username']} (password: sales123)"))
            else:
                self.stdout.write(self.style.WARNING(f"Sales account {member['username']} already exists"))
        
        self.stdout.write(self.style.SUCCESS('\nAll synthetic accounts created successfully!'))
        self.stdout.write(self.style.SUCCESS('\nLogin Credentials:'))
        self.stdout.write(self.style.SUCCESS('Manager: username=manager, password=manager123'))
        self.stdout.write(self.style.SUCCESS('Sales Team: username=sales1/sales2/sales3, password=sales123'))
