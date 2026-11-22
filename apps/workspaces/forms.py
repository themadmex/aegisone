from django import forms

from apps.accounts.models import normalize_email


class InviteForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        label="Email address",
        error_messages={"invalid": "Enter a full email address, like name@company.com."},
        widget=forms.EmailInput(attrs={"autocomplete": "off", "placeholder": "colleague@company.com"}),
    )

    def clean_email(self):
        return normalize_email(self.cleaned_data["email"])
