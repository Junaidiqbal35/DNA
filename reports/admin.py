from django.contrib import admin
from .models import Reports

from .models import generate_user_verification_code


# Register your models here.
@admin.register(Reports)
class ReportsAdmin(admin.ModelAdmin):
    list_display = (
        'patient_chasing_number', 'patient_name', 'patient_phone_number', 'pin_code', 'patient_report', 'created_at')
    list_filter = ('patient_city',)
    search_fields = ('pin_code', 'patient_name', 'patient_phone_number')
# prepopulated_fields = {'pin_code': (generate_user_verification_code(), )}
# raw_id_fields = ('author',)
# date_hierarchy = 'publish'
# ordering = ('status', 'publish')
