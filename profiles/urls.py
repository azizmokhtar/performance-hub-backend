from django.urls import path
from .views import PositionListView, SpecialtyListView, LicenseListView

urlpatterns = [
    path("positions/", PositionListView.as_view(), name="positions-list"),
    path("specialties/", SpecialtyListView.as_view(), name="specialties-list"),
    path("licenses/", LicenseListView.as_view(), name="licenses-list"),
]
