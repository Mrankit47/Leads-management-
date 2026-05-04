from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from leads.models import UserProfile
import os

User = get_user_model()

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        # delete old user
        User.objects.filter(username=username).delete()

        # create new user (with proper hashing)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        user.is_staff = True
        user.is_superuser = True
        user.save()

        # 🔥 IMPORTANT (ye tumhari problem fix karega)
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "role": "SUPERADMIN",
                "is_active": True
            }
        )

        print("✅ Superadmin created")