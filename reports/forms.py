from django import forms


class ReportSearchForm(forms.Form):
    patient_number = forms.CharField(max_length=255)
    pin_code = forms.CharField(max_length=6)

    class Meta:
        fields = ['patient_number', 'pin_code']
