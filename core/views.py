from django.shortcuts import render, get_object_or_404

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


def product_detail(request, slug):
    product = get_object_or_404(Product,
                                slug=slug,
                                available=True)
    cart_product_form = CartAddProductForm()
    return render(request,
                  'pages/product_detail.html',
                  {'product': product, 'cart_product_form': cart_product_form})


def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            # messages.success(request, 'Successfully Send the messages!!')
            return render(request, 'pages/thankyou.html')

    else:
        form = ContactForm()
    return render(request, 'pages/contactus.html', context={'form': form})
