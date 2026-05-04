from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from leads.models import UserProfile
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Create or update superadmin"

    def handle(self, *args, **kwargs):

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "superadmin")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@gmail.com")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Admin@123")

        user, created = User.objects.get_or_create(username=username)

        user.email = email
        user.set_password(password)   # 🔥 password hashing fix
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        # 🔥 ensure profile exists
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "role": "superadmin",   # ⚠️ lowercase रखना (tumhara code yahi expect karta hai)
                "is_active": True
            }
        )

        self.stdout.write(self.style.SUCCESS("✅ Superadmin created/updated"))