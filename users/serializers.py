from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.password_validation import validate_password

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'password', 'password2')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': True},
        }

    def validate(self, attrs):
        attrs['email'] = attrs['email'].strip().lower()
        if CustomUser.objects.filter(email__iexact=attrs['email']).exists():
            raise serializers.ValidationError({"email": "A user with that email already exists."})
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, vd):
        vd.pop('password2')
        user = CustomUser.objects.create_user(
            email=vd['email'], first_name=vd['first_name'], last_name=vd['last_name'],
            role=vd['role'], password=vd['password'],
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'profile_picture')
        read_only_fields = ('email', 'role')

class UserTeamListSerializer(serializers.ModelSerializer):
    # pure user snapshot used in some lists; no more football fields
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'profile_picture')

class AdminUserUpdateSerializer(UserProfileSerializer):
    class Meta(UserProfileSerializer.Meta):
        read_only_fields = ('email',)
        # admin can change first/last/role/profile_picture if you want:
        # fields = ('id','email','first_name','last_name','role','profile_picture')

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
