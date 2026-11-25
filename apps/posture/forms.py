from django import forms

from .catalog import CHOICES
from .dns_records import normalize_domain
from .models import Action, DataRequest


class RevisionForm(forms.Form):
    revision = forms.IntegerField(min_value=0, max_value=2147483647, widget=forms.HiddenInput)


class AnswerForm(RevisionForm):
    answer = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect)


class ActionStatusForm(RevisionForm):
    status = forms.ChoiceField(choices=Action.Status.choices)


class ReportForm(forms.Form):
    version = forms.CharField(max_length=64, min_length=64, widget=forms.HiddenInput)


class DataRequestForm(forms.Form):
    kind = forms.ChoiceField(choices=DataRequest.Kind.choices, widget=forms.HiddenInput)
    confirmed = forms.BooleanField(label="I confirm this request for my workspace")


class DomainForm(forms.Form):
    name = forms.CharField(label="Exact domain name", max_length=253)
    sends_mail = forms.BooleanField(label="We use this domain to send email", required=False)
    attest = forms.BooleanField(label="I am authorized to verify and check this domain")

    def clean_name(self):
        return normalize_domain(self.cleaned_data["name"])
