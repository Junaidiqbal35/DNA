from django.contrib import admin

# Register your models here.
from core.models import Contact, Product


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price',
                    'available', 'created', 'updated']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'available']
    prepopulated_fields = {'slug': ('name',)}


class ContactAdminPanel(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone_number', 'message', 'sent_at']


admin.site.register(Product, ProductAdmin)
admin.site.register(Contact, ContactAdminPanel)
