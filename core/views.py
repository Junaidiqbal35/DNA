from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

# Create your views here.


from django.views.generic import TemplateView

from cart.forms import CartAddProductForm
from core.forms import ContactForm
from core.models import Product


def home(request):
    return render(request,
                  'pages/home.html')


def product_list(request):
    products = Product.objects.filter(available=True)

    return render(request, 'pages/index.html', {'products': products})


def product_list_dynamic(request):
    """New view for index2.html with dynamic product loading"""
    products = Product.objects.filter(available=True).order_by('-created')

    return render(request, 'pages/index2.html', {'products': products})


def services_view(request):
    """Services page with all available products"""
    products = Product.objects.filter(available=True).order_by('-created')
    return render(request, 'pages/services.html', {'products': products})


def get_product_list(request):
    products = Product.objects.filter(available=True)
    return render(request, 'partials/_get_product_list.html', {'products': products})


def get_products_json(request):
    """API endpoint to get products in JSON format for navbar dropdown"""
    products = Product.objects.filter(available=True).values(
        'id', 'name', 'slug', 'price', 'discounted_price'
    )

    products_list = []
    for product in products:
        products_list.append({
            'id': product['id'],
            'name': product['name'],
            'slug': product['slug'],
            'price': product['price'],
            'discounted_price': product['discounted_price'],
            'url': f"/product/{product['slug']}/"
        })

    return JsonResponse({'products': products_list})


def product_detail(request, slug):
    product = get_object_or_404(Product,
                                slug=slug,
                                available=True)
    recommended_products = Product.objects.filter(available=True).exclude(id=product.id)[:4]
    cart_product_form = CartAddProductForm()

    # Define addon options for DNA tests
    addon_options = [
        {
            'id': 'additional_child',
            'name': 'Additional Child',
            'description': 'Add another child to the paternity test',
            'price': 8000,
            'applicable_to': ['paternity', 'relationship']
        },
        {
            'id': 'additional_parent',
            'name': 'Additional Parent (Mother/Father)',
            'description': 'Include mother or father sample for enhanced accuracy',
            'price': 6000,
            'applicable_to': ['paternity', 'relationship']
        },
        {
            'id': 'additional_sibling',
            'name': 'Additional Sibling',
            'description': 'Add sibling sample for relationship testing',
            'price': 7000,
            'applicable_to': ['relationship', 'sibling']
        },
        {
            'id': 'express_processing',
            'name': 'Express Processing (12-24 hours)',
            'description': 'Get results in 12-24 hours instead of standard time',
            'price': 10000,
            'applicable_to': ['paternity', 'relationship', 'immigration']
        },
        {
            'id': 'home_collection',
            'name': 'Home Collection Service',
            'description': 'Professional sample collection at your location',
            'price': 5000,
            'applicable_to': ['all']
        },
        {
            'id': 'genetic_counseling',
            'name': 'Genetic Counseling Session',
            'description': 'One-on-one consultation with genetic counselor',
            'price': 7500,
            'applicable_to': ['health', 'prenatal', 'ancestry']
        }
    ]

    return render(request,
                  'pages/product_detail.html',
                  {
                      'product': product,
                      'cart_product_form': cart_product_form,
                      'recommended_products': recommended_products,
                      'addon_options': addon_options
                  })


def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_instance = form.save(commit=False)
            body = f'{contact_instance.message}\n\nEmail: {contact_instance.email}\nContact Phone Number: {contact_instance.phone_number}.'
            send_mail(
                'Query Email By The Customer',
                body,
                'info@dnalabpakistan.com',
                ['nasir@dnalabpakistan.com'],
                fail_silently=False,
            )
            contact_instance.save()

            # messages.success(request, 'Successfully Send the messages!!')
            return render(request, 'pages/thankyou.html')

    else:
        form = ContactForm()
    return render(request, 'pages/contactus.html', context={'form': form})