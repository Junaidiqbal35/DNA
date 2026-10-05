from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CompanyCredential, Contact, LabCertification, PartnerLab, Product,
)


class LabCertificationInline(admin.TabularInline):
    model = LabCertification
    extra = 1
    fields = ('kind', 'title', 'issuing_body', 'reference', 'image',
              'document', 'valid_until', 'display_order', 'is_active', 'preview')
    readonly_fields = ('preview',)

    @admin.display(description='Preview')
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="height:70px;border:1px solid #ddd">',
                obj.image.url)
        return '—'


@admin.register(PartnerLab)
class PartnerLabAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'city', 'handles_legal_tests',
                    'certificate_count', 'is_active', 'display_order')
    list_filter = ('country', 'is_active', 'handles_legal_tests')
    list_editable = ('is_active', 'display_order')
    search_fields = ('name', 'city', 'accreditations')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [LabCertificationInline]

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'is_active', 'display_order')}),
        ('Where it is', {'fields': ('country', 'city', 'website')}),
        ('What customers see', {'fields': ('logo', 'summary', 'description')}),
        ('Credentials', {
            'fields': ('accreditations', 'handles_legal_tests'),
            'description': (
                'Only list accreditations this laboratory actually holds. They '
                'display to customers as credentials, and they belong to the '
                'laboratory — never to the Pakistan office.'),
        }),
    )

    @admin.display(description='Certificates')
    def certificate_count(self, obj):
        return obj.certifications.filter(is_active=True).count()


@admin.register(LabCertification)
class LabCertificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'lab', 'kind', 'issuing_body', 'reference',
                    'valid_until', 'expired', 'is_active')
    list_filter = ('lab', 'kind', 'is_active', 'issuing_body')
    search_fields = ('title', 'issuing_body', 'reference')

    @admin.display(description='Expired', boolean=True)
    def expired(self, obj):
        return obj.is_expired


@admin.register(CompanyCredential)
class CompanyCredentialAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'issuer', 'issued_year',
                    'valid_until', 'expired', 'is_active', 'display_order')
    list_filter = ('kind', 'is_active')
    list_editable = ('is_active', 'display_order')
    search_fields = ('title', 'issuer', 'reference')

    @admin.display(description='Expired', boolean=True)
    def expired(self, obj):
        return obj.is_expired


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'sample_type', 'price',
                    'discounted_price', 'partner_lab', 'available')
    list_filter = ('available', 'category', 'sample_type', 'partner_lab')
    list_editable = ('price', 'discounted_price', 'available')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'sent_at')
    search_fields = ('name', 'email', 'phone_number')
