from django.contrib import admin

from .models import Contact, Interaction


class InteractionInline(admin.TabularInline):
    model = Interaction
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "stage", "follow_up_date", "created_at")
    list_filter = ("stage",)
    search_fields = ("name", "company", "email")
    inlines = [InteractionInline]
