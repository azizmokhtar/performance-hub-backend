# profiles/views.py
from rest_framework import generics, permissions
from .models import Position
from .serializers import PositionSerializer

class PositionListView(generics.ListAPIView):
    queryset = Position.objects.all().order_by("line", "name")
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]  # or AllowAny if you prefer
from rest_framework import generics, permissions
from .models import Position, Specialty, License
from .serializers import PositionSerializer, SpecialtySerializer, LicenseSerializer

class PositionListView(generics.ListAPIView):
    queryset = Position.objects.all().order_by('line', 'name')
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]

class SpecialtyListView(generics.ListAPIView):
    queryset = Specialty.objects.all().order_by('name')
    serializer_class = SpecialtySerializer
    permission_classes = [permissions.IsAuthenticated]

class LicenseListView(generics.ListAPIView):
    queryset = License.objects.all().order_by('name')
    serializer_class = LicenseSerializer
    permission_classes = [permissions.IsAuthenticated]
