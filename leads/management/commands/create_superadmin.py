from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from leads.models import UserProfile

class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        username = "superadmin"
        password = "admin123"

        user = User.objects.create_user(username=username, password=password)

        profile = user.userprofile
        profile.role = "superadmin"
        profile.save()

        print("Superadmin created")