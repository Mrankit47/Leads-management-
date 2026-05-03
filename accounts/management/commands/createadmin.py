from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if username and password:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username, email, password)
                self.stdout.write("Superuser created")
            else:
                self.stdout.write("Superuser already exists")
                user = User.objects.create_superuser(username, email, password)

                # अगर UserProfile है
                from leads.models import UserProfile

                UserProfile.objects.create(
    user=user,
    role='SUPERADMIN'
)