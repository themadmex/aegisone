from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import PasswordChangeForm
from django.core.validators import MaxLengthValidator

from .models import normalize_email


class SignInForm(forms.Form):
    email = forms.EmailField(
        max_length=254, label="Work email", widget=forms.EmailInput(attrs={"autocomplete": "username"})
    )
    password = forms.CharField(
        max_length=256, label="Password", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean_email(self):
        return normalize_email(self.cleaned_data["email"])


class CodeForm(forms.Form):
    code = forms.CharField(
        max_length=16, label="Code",
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "spellcheck": "false"}),
    )

    def clean_code(self):
        return "".join(self.cleaned_data["code"].split())


class SetPasswordForm(forms.Form):
    password = forms.CharField(
        max_length=256, label="Create a password", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 12 characters. A short phrase is easiest to remember.",
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        password_validation.validate_password(password, self.user)
        return password


class AcceptInviteForm(SetPasswordForm):
    name = forms.CharField(max_length=120, label="Your name", widget=forms.TextInput(attrs={"autocomplete": "name"}))
    field_order = ["name", "password"]


class RecoveryRequestForm(forms.Form):
    email = forms.EmailField(max_length=254, label="Work email", widget=forms.EmailInput(attrs={"autocomplete": "username"}))

    def clean_email(self):
        return normalize_email(self.cleaned_data["email"])


class ProfileForm(forms.Form):
    name = forms.CharField(label="Display name", max_length=120, widget=forms.TextInput(attrs={"autocomplete": "name"}))


class ChangePasswordForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.max_length = 256
            field.validators.append(MaxLengthValidator(256))
            field.widget.attrs["maxlength"] = 256
        self.fields["new_password1"].help_text = "At least 12 characters. A short phrase is easiest to remember."
