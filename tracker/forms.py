from django import forms

from .models import Contact, Interaction


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "email", "company", "stage", "follow_up_date", "tags"]
        labels = {"follow_up_date": "Follow-up date"}
        widgets = {
            "follow_up_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "tags": forms.CheckboxSelectMultiple,
        }


class InteractionForm(forms.ModelForm):
    class Meta:
        model = Interaction
        fields = ["kind", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3, "placeholder": "What did you talk about? What's next?"})}
