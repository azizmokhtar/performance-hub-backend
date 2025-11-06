# users/managers.py
from django.contrib.auth.base_user import BaseUserManager

ROLE_FLAGS = {
    'PLAYER':  dict(is_staff=False, is_superuser=False),
    'COACH':   dict(is_staff=True,  is_superuser=False),
    'STAFF':   dict(is_staff=True,  is_superuser=False),
    'ADMIN':   dict(is_staff=True,  is_superuser=False),
}

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _apply_role_flags(self, extra_fields):
        role = extra_fields.get('role')
        if role in ROLE_FLAGS:
            # Only set if caller didn't explicitly set flags
            extra_fields.setdefault('is_staff', ROLE_FLAGS[role]['is_staff'])
            extra_fields.setdefault('is_superuser', ROLE_FLAGS[role]['is_superuser'])
        else:
            # Safe defaults for unknown role
            extra_fields.setdefault('is_staff', False)
            extra_fields.setdefault('is_superuser', False)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        self._apply_role_flags(extra_fields)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


"""
 Admin access

Any user with is_staff=True can log into /admin/.

If you want only “real” Django superusers in /admin/, keep COACH/STAFF/ADMIN with is_staff=False. If you want coaches/staff to manage data via Django admin, keep them is_staff=True. Your call.
"""