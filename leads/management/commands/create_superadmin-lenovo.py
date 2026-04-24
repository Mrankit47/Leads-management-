from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from leads.models import UserProfile

class Command(BaseCommand):
    help = 'Create a superadmin user'

    def handle(self, *args, **kwargs):
        username = "superadmin"
        password = "admin123"

        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username=username, password=password)
            profile = user.userprofile
            profile.role = "superadmin"
            profile.save()
            self.stdout.write(self.style.SUCCESS("Superadmin created"))
        else:
            self.stdout.write(self.style.WARNING("Superadmin already exists"))