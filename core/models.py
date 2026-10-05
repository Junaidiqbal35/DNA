from django.db import models
from django.urls import NoReverseMatch, reverse
from ckeditor.fields import RichTextField


# Create your models here.
class Product(models.Model):
    """A test in the catalogue.

    `category` and `sample_type` were added because the real catalogue is ~30
    tests spanning relationship work, immigration work and clinical genetics.
    One flat list is unusable, and — more importantly — a large share of the
    clinical tests need an EDTA blood draw rather than the buccal swab the
    Pakistan office coordinate. That difference has to be visible before someone
    books, not discovered at the appointment.
    """

    class Category(models.TextChoices):
        RELATIONSHIP = 'relationship', 'Relationship testing'
        IMMIGRATION = 'immigration', 'Immigration & legal'
        PRENATAL = 'prenatal', 'Prenatal testing'
        CLINICAL = 'clinical', 'Clinical & hereditary'
        WELLNESS = 'wellness', 'Wellness & lifestyle'
        ANCESTRY = 'ancestry', 'Ancestry'
        OTHER = 'other', 'Other services'

    class SampleType(models.TextChoices):
        SWAB = 'swab', 'Buccal (cheek) swab'
        BLOOD = 'blood', 'Blood sample'
        MATERNAL_BLOOD = 'maternal_blood', "Mother's blood sample"
        TISSUE = 'tissue', 'Tissue sample'
        OTHER = 'other', 'Other — ask us'

    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d',
                              blank=True)
    description = RichTextField(blank=True)
    price = models.PositiveBigIntegerField()
    discounted_price = models.PositiveBigIntegerField(blank=True, null=True)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER,
        db_index=True,
        help_text='Groups the test on the services page.',
    )
    sample_type = models.CharField(
        max_length=20, choices=SampleType.choices, blank=True,
        help_text='Leave blank if unsure. Anything other than a cheek swab '
                  'cannot be collected at the Pakistan office and needs a '
                  'clinical collection partner — say so before someone books.',
    )

    # Which overseas laboratory normally handles this test. Optional, because
    # not every product maps to exactly one lab.
    partner_lab = models.ForeignKey(
        'PartnerLab',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text='The partner laboratory that normally runs this test.',
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['name']),
            models.Index(fields=['-created']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:product_detail',
                       args=[self.slug])

    @property
    def discount_amount(self):
        """Calculate the discount amount if discounted_price exists"""
        if self.discounted_price and self.discounted_price < self.price:
            return self.price - self.discounted_price
        return 0

    @property
    def discount_percentage(self):
        """Calculate the discount percentage"""
        if self.discounted_price and self.discounted_price < self.price:
            return round(((self.price - self.discounted_price) / self.price) * 100)
        return 0

    @property
    def needs_clinical_collection(self):
        """True when the sample cannot be taken at the Pakistan office."""
        return self.sample_type in {
            self.SampleType.BLOOD,
            self.SampleType.MATERNAL_BLOOD,
            self.SampleType.TISSUE,
        }

    @property
    def is_health_related(self):
        """Clinical, prenatal and wellness results carry health meaning, so
        these need the 'discuss it with a clinician' note."""
        return self.category in {
            self.Category.CLINICAL,
            self.Category.PRENATAL,
            self.Category.WELLNESS,
        }

    @property
    def effective_price(self):
        """Return the effective price (discounted if available, otherwise price)"""
        return self.discounted_price if self.discounted_price else self.price


class PartnerLab(models.Model):
    """An overseas laboratory that actually performs the testing.

    These are the business's main trust asset, so they are content you manage
    in the admin rather than logos hardcoded into a template. Logos and
    certificates upload to MEDIA, so adding a lab needs no deploy and no
    collectstatic run.
    """

    class Country(models.TextChoices):
        UK = 'GB', 'United Kingdom'
        USA = 'US', 'United States'
        Turkey = 'AU', 'Turkey'

    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    country = models.CharField(max_length=2, choices=Country.choices)
    city = models.CharField(
        max_length=120, blank=True,
        help_text='Optional. City the laboratory operates from.',
    )

    logo = models.ImageField(upload_to='labs/logos/', blank=True)
    website = models.URLField(blank=True)

    summary = models.CharField(
        max_length=300, blank=True,
        help_text='One line shown on cards, e.g. what this lab specialises in.',
    )
    description = RichTextField(
        blank=True,
        help_text='Longer description shown on the partners page.',
    )

    accreditations = models.CharField(
        max_length=300, blank=True,
        help_text="Comma separated, e.g. 'ISO 17025, AABB'. Only list what the "
                  "lab actually holds — these appear as credentials.",
    )

    handles_legal_tests = models.BooleanField(
        default=False,
        help_text='Tick if this lab issues reports for legal and immigration use.',
    )

    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(
        default=True,
        help_text='Untick to hide a lab without deleting it — use this the '
                  'moment an agreement lapses.',
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Partner laboratory'
        verbose_name_plural = 'Partner laboratories'

    def __str__(self):
        return f'{self.name} ({self.get_country_display()})'

    def get_absolute_url(self):
        # Falls back to a plain path so a missing URL name cannot take the
        # whole site down before you have wired up urls.py.
        try:
            return reverse('partners') + f'#{self.slug}'
        except NoReverseMatch:
            return f'/partners/#{self.slug}'

    @property
    def accreditation_list(self):
        """accreditations as a clean list for templates."""
        return [a.strip() for a in self.accreditations.split(',') if a.strip()]

    @property
    def initials(self):
        """Fallback shown when no logo has been uploaded yet."""
        return ''.join(word[0] for word in self.name.split()[:2]).upper()


class LabCertification(models.Model):
    """A certificate or accreditation document belonging to a partner lab.

    The certificate is evidence, so it is attached to the lab that holds it.
    Never attach one to the Pakistan office — that office holds no laboratory
    accreditation.
    """

    class Kind(models.TextChoices):
        ACCREDITATION = 'accreditation', "Laboratory's own accreditation"
        AUTHORIZATION = 'authorization', 'Authorisation issued to us by this lab'

    lab = models.ForeignKey(
        PartnerLab, on_delete=models.CASCADE, related_name='certifications',
    )
    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.ACCREDITATION,
        help_text="'Accreditation' belongs to the laboratory. 'Authorisation' "
                  'is a document that laboratory issued to DNA Testing '
                  'Solutions — such as an authorised-collector certificate. '
                  'The two are displayed separately and must not be mixed.',
    )
    title = models.CharField(
        max_length=200,
        help_text="e.g. 'ISO/IEC 17025:2017 accreditation'",
    )
    issuing_body = models.CharField(
        max_length=200, blank=True,
        help_text="e.g. 'UKAS', 'AABB'",
    )
    reference = models.CharField(
        max_length=100, blank=True,
        help_text='Certificate or schedule number, shown in monospace.',
    )
    image = models.ImageField(
        upload_to='labs/certificates/',
        help_text='Scan or photo of the certificate. JPG or PNG.',
    )
    document = models.FileField(
        upload_to='labs/certificates/docs/', blank=True,
        help_text='Optional PDF of the same certificate.',
    )
    valid_until = models.DateField(
        null=True, blank=True,
        help_text='Optional. Lets you spot an expired certificate before a '
                  'customer does.',
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = 'Laboratory certificate'
        verbose_name_plural = 'Laboratory certificates'

    def __str__(self):
        return f'{self.lab.name} — {self.title}'

    @property
    def is_expired(self):
        if not self.valid_until:
            return False
        from django.utils import timezone
        return self.valid_until < timezone.localdate()


class CompanyCredential(models.Model):
    """A document DNA Testing Solutions itself holds.

    Kept separate from LabCertification on purpose. A laboratory accreditation
    belongs to the laboratory; an authorised-collector certificate, a quality
    manual or a courier sustainability certificate belongs to this company.
    Showing them in one undifferentiated row of logos is exactly how a
    collection office ends up looking like it holds laboratory accreditation.
    """

    class Kind(models.TextChoices):
        AUTHORIZATION = 'authorization', 'Authorisation / appointment'
        QUALITY = 'quality', 'Quality management'
        ENVIRONMENT = 'environment', 'Environmental'
        OTHER = 'other', 'Other'

    title = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.OTHER,
    )
    issuer = models.CharField(
        max_length=200, blank=True,
        help_text='Who issued it, e.g. Universal Forensics Corporation.',
    )
    summary = models.CharField(
        max_length=300, blank=True,
        help_text='One line explaining what it actually means for a customer.',
    )
    reference = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='credentials/', blank=True)
    document = models.FileField(upload_to='credentials/docs/', blank=True)
    issued_year = models.PositiveSmallIntegerField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = 'Company credential'
        verbose_name_plural = 'Company credentials'

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        if not self.valid_until:
            return False
        from django.utils import timezone
        return self.valid_until < timezone.localdate()


class Contact(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    message = models.TextField()
    phone_number = models.CharField(max_length=15)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.name
