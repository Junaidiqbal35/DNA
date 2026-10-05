from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import NoReverseMatch, reverse

from core.forms import ContactForm
from core.models import (
    CompanyCredential, LabCertification, PartnerLab, Product,
)

# The cart app lives outside this repo folder in some checkouts. Importing it
# at module level meant that if it was missing, every single view in the site
# failed with ImportError — including pages that have nothing to do with a
# cart. Degrade instead: product detail still renders, just without the
# add-to-cart form.
try:
    from cart.forms import CartAddProductForm
except ImportError:  # pragma: no cover - depends on deployment layout
    CartAddProductForm = None


# --------------------------------------------------------------------------
# Shared querysets
# --------------------------------------------------------------------------

def active_labs():
    """Partner laboratories to show, with their live documents attached.

    One queryset for every page that mentions the labs, so switching a lab off
    in the admin removes it everywhere at once.
    """
    return (
        PartnerLab.objects
        .filter(is_active=True)
        .prefetch_related(
            Prefetch(
                'certifications',
                queryset=LabCertification.objects.filter(is_active=True),
                to_attr='live_certifications',
            )
        )
    )


def active_credentials():
    return CompanyCredential.objects.filter(is_active=True)


def available_products():
    return (
        Product.objects
        .filter(available=True)
        .select_related('partner_lab')
    )


def group_products(products):
    """Group a product list by category, keeping the declared order."""
    buckets = {key: [] for key, _ in Product.Category.choices}
    for product in products:
        buckets.setdefault(product.category, []).append(product)

    labels = dict(Product.Category.choices)
    health_related = {
        Product.Category.CLINICAL,
        Product.Category.PRENATAL,
        Product.Category.WELLNESS,
    }
    return [
        {
            'key': key,
            'label': labels.get(key, key),
            'products': items,
            'is_health_related': key in health_related,
        }
        for key, items in buckets.items() if items
    ]


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

FEATURED_TEST_SLUGS = ["nutrition-dna", "sports-dna", "microbiome"]




def home(request):
    labs = list(active_labs())
    available = Product.objects.filter(available=True)
    featured = sorted(
        available.filter(slug__in=FEATURED_TEST_SLUGS),
        key=lambda p: FEATURED_TEST_SLUGS.index(p.slug),
    )
    

    return render(request, 'pages/home.html', {
        'products': available_products().order_by('-created')[:6],
        "featured_products": featured,
        'partner_labs': labs,
        'company_credentials': active_credentials(),
    })


def services_view(request):
    """Services page — tests grouped by category.

    The catalogue runs to roughly thirty tests spanning relationship work,
    immigration work and clinical genetics. A single flat grid is unusable at
    that size, and it also sits a paternity swab next to a cancer panel.
    """
    products = list(available_products().order_by('name'))
    return render(request, 'pages/services.html', {
        'products': products,
        'product_groups': group_products(products),
        'partner_labs': active_labs(),
        'needs_clinical_collection': any(
            product.needs_clinical_collection for product in products
        ),
    })


def partners_view(request):
    """The laboratories page — who performs the testing, and what they hold."""
    labs = active_labs()

    country_labels = dict(PartnerLab.Country.choices)
    countries = (
        PartnerLab.objects
        .filter(is_active=True)
        .values('country')
        .annotate(total=Count('id'))
        .order_by('country')
    )

    return render(request, 'pages/partners.html', {
        'partner_labs': labs,
        'company_credentials': active_credentials(),
        'countries': [
            {'name': country_labels.get(row['country'], row['country']),
             'total': row['total']}
            for row in countries
        ],
        'certificate_total': LabCertification.objects.filter(
            is_active=True, lab__is_active=True,
        ).count(),
    })


def about_view(request):
    """About page.

    This was a bare TemplateView, so the partner section silently fell back to
    a plain list of country names no matter how many labs were in the admin.
    """
    return render(request, 'pages/aboutus.html', {
        'partner_labs': active_labs(),
        'company_credentials': active_credentials(),
    })


def paternity_view(request):
    """The standalone paternity testing page."""
    product = Product.objects.filter(
        available=True, category=Product.Category.RELATIONSHIP,
    ).select_related('partner_lab').order_by('price').first()

    return render(request, 'pages/product.html', {
        'product': product,
        'partner_labs': active_labs(),
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('partner_lab'),
        slug=slug,
        available=True,
    )
    recommended = (
        available_products()
        .filter(category=product.category)
        .exclude(id=product.id)[:4]
    )

    # Add-ons for DNA test orders.
    #
    # CHANGED — two of the old entries contradicted the business model:
    #
    #   'Express Processing (12-24 hours)' cannot be promised. The sample has
    #   to clear a Pakistan-to-overseas courier leg before testing even starts.
    #   Replaced with priority courier, which shortens transit and says so.
    #
    #   'Genetic Counseling Session' cuts straight across the disclaimer — the
    #   Pakistan office provides no genetic or medical interpretation. Removed.
    addon_options = [
        {
            'id': 'additional_child',
            'name': 'Additional child',
            'description': 'Add another child to the test',
            'price': 8000,
            'applicable_to': ['relationship'],
        },
        {
            'id': 'additional_parent',
            'name': 'Additional parent (mother or father)',
            'description': "Include a parent's sample to strengthen the comparison",
            'price': 6000,
            'applicable_to': ['relationship'],
        },
        {
            'id': 'priority_courier',
            'name': 'Priority courier to the laboratory',
            'description': 'Fastest available DHL service, airway bill shared the '
                           'same day. Shortens transit, not the laboratory\'s own '
                           'processing time.',
            'price': 10000,
            'applicable_to': ['all'],
        },
        {
            'id': 'collection_kit_delivery',
            'name': 'Collection kit delivered to your city',
            'description': 'For personal-knowledge tests only. Legal and '
                           'immigration tests need witnessed collection.',
            'price': 5000,
            'applicable_to': ['relationship'],
        },
        {
            'id': 'extra_report_copy',
            'name': 'Additional report copies',
            'description': 'Extra certified copies of the laboratory\'s report',
            'price': 3500,
            'applicable_to': ['all'],
        },
    ]

    # Resolved here rather than with {% url %} in the template, because the
    # order app is optional and a missing name would take the page down.
    try:
        checkout_url = reverse('order_checkout')
    except NoReverseMatch:
        checkout_url = ''

    return render(request, 'pages/product_detail.html', {
        'product': product,
        'checkout_url': checkout_url,
        'cart_product_form': CartAddProductForm() if CartAddProductForm else None,
        'recommended_products': recommended,
        'addon_options': addon_options,
    })


def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            body = (
                f'{contact.message}\n\n'
                f'Email: {contact.email}\n'
                f'Contact Phone Number: {contact.phone_number}.'
            )
            send_mail(
                'Query Email By The Customer',
                body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_NOTIFY_EMAIL],
                # The enquiry is already saved. A mail outage should not show
                # the customer an error page for a message we did receive.
                fail_silently=True,
            )
            return render(request, 'pages/thankyou.html')
    else:
        form = ContactForm()

    return render(request, 'pages/contactus.html', {'form': form})


# --------------------------------------------------------------------------
# Fragments / API
# --------------------------------------------------------------------------

def get_product_list(request):
    return render(request, 'partials/_get_product_list.html', {
        'products': available_products(),
    })


def get_products_json(request):
    products = available_products().values(
        'id', 'name', 'slug', 'price', 'discounted_price', 'category',
    )
    return JsonResponse({'products': [
        {**product, 'url': f"/product/{product['slug']}/"}
        for product in products
    ]})
