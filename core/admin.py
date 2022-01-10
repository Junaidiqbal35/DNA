from django.contrib import admin

# Register your models here.
from core.models import Contact


class ContactAdminPanel(admin.ModelAdmin):

    list_display = ['name', 'email', 'phone_number', 'message', 'sent_at']


admin.site.register(Contact, ContactAdminPanel)
