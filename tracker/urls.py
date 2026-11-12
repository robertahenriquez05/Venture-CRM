from django.urls import path

from . import views

urlpatterns = [
    path("", views.contact_list, name="contact_list"),
    path("contacts/<int:pk>/", views.contact_detail, name="contact_detail"),
    path("contacts/<int:pk>/interactions/", views.log_interaction, name="log_interaction"),
]
