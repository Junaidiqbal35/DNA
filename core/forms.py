from django.forms import ModelForm

from core.models import Contact


class ContactForm(ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'phone_number', 'message', ]
