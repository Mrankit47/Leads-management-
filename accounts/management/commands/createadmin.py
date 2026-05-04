from django.contrib.auth import get_user_model
from leads.models import UserProfile
import os

User = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

# delete old user (important)
User.objects.filter(username=username).delete()

# create new user
user = User.objects.create_user(
    username=username,
    email=email,
    password=password
)

user.is_staff = True
user.is_superuser = True
user.save()

# 🔥 THIS IS THE REAL FIX
UserProfile.objects.update_or_create(
    user=user,
    defaults={
        "role": "SUPERADMIN",   # exact same as your system expects
        "is_active": True
    }
)

print("✅ Superadmin created successfully")