# profiles/serializers.py
from rest_framework import serializers
from .models import Position

from rest_framework import serializers
from .models import Position, Specialty, License

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ('id', 'key', 'name', 'line')

class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ('id', 'key', 'name')

class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = License
        fields = ('id', 'key', 'name', 'issuer')
