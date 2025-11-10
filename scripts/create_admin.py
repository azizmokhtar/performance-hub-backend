# scripts/create_admin.py
from django.contrib.auth import get_user_model

User = get_user_model()

email = "mohamedazizelmokhtar27@gmail.com"
password = "1234567890"

# If user already exists, skip creation
if not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name="Mohamed Aziz",
        last_name="El Mokhtar",
        role="ADMIN",
    )
    print(f"✅ Admin user created: {email}")
else:
    print(f"⚠️ User already exists: {email}")
