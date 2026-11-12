from django.contrib import admin

from .models import Contact, Interaction, StageChange, Tag


class InteractionInline(admin.TabularInline):
    model = Interaction
    extra = 0
    readonly_fields = ("created_at",)


class StageChangeInline(admin.TabularInline):
    """Read-only: stage history is append-only (ADR-002)."""

    model = StageChange
    extra = 0
    can_delete = False
    readonly_fields = ("from_stage", "to_stage", "changed_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "stage", "follow_up_date", "created_at")
    list_filter = ("stage", "tags")
    search_fields = ("name", "company", "email")
    filter_horizontal = ("tags",)
    inlines = [InteractionInline, StageChangeInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
