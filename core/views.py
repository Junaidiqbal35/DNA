from django.shortcuts import render, get_object_or_404

# Create your views here.


from django.views.generic import TemplateView

from core.forms import ContactForm
from core.models import Product


def home(request):
    return render(request,
                  'pages/home.html')


# def product_list(request):
#     products = Product.objects.filter(available=True)
#
#     return render(request,
#                   'shop/product/list.html',
#                   {
#                       'products': products})
#
#
# def product_detail(request, id, slug):
#     product = get_object_or_404(Product,
#                                 id=id,
#                                 slug=slug,
#                                 available=True)
#     return render(request,
#                   'shop/product/detail.html',
#                   {'product': product})


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
