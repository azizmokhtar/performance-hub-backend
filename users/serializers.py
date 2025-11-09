from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.password_validation import validate_password

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'team', 'password', 'password2')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': True},
            'team': {'required': False, 'allow_null': True}, # Team can be assigned later
        }

    def validate(self, attrs):
        # normalize email
        email = attrs.get('email', '')
        attrs['email'] = email.strip().lower()

        # enforce CI uniqueness at serializer layer (nice UX)
        from .models import CustomUser
        if CustomUser.objects.filter(email__iexact=attrs['email']).exists():
            raise serializers.ValidationError({"email": "A user with that email already exists."})

        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        # Remove password2 as it's not part of the model
        validated_data.pop('password2')
        # Ensure 'team' is handled correctly if not provided
        team_instance = validated_data.pop('team', None)

        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=validated_data['role'],
            password=validated_data['password'],
        )
        if team_instance:
            user.team = team_instance
            user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

class UserProfileSerializer(serializers.ModelSerializer):
    # Make team field read-only or restrict modification based on permissions
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'first_name', 'last_name', 'role', 'team', 'team_name',
            'date_of_birth', 'jersey_number', 'position', 'profile_picture'
        )
        read_only_fields = ('email', 'role', 'team', 'team_name') # These should generally not be mutable by users themselves
        extra_kwargs = {
            'password': {'write_only': True, 'required': False} # Allow password change
        }

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)

class UserTeamListSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'jersey_number', 'position', 'profile_picture', 'team_name')

class AdminUserUpdateSerializer(UserProfileSerializer):
    class Meta(UserProfileSerializer.Meta):
        read_only_fields = ('email', 'team_name')  # allow 'team' and 'role' to be writable for admins