from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.contact_list, name="contact_list"),
    path("pipeline/", views.pipeline, name="pipeline"),
    path("contacts/<int:pk>/", views.contact_detail, name="contact_detail"),
    path("contacts/<int:pk>/interactions/", views.log_interaction, name="log_interaction"),
    path("contacts/<int:pk>/stage/", views.move_stage, name="move_stage"),
    path("contacts/<int:pk>/delete/", views.delete_contact, name="delete_contact"),
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("healthz", views.healthz, name="healthz"),
]
