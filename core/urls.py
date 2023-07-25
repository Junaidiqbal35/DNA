from django.urls import path
from django.views.generic import TemplateView
from .views import contact_us

from .views import home

urlpatterns = [
    path('', TemplateView.as_view(template_name="pages/home.html"), name='home'),
    path('services/', TemplateView.as_view(template_name="pages/services.html"), name='service'),
    path('product/', TemplateView.as_view(template_name="pages/product.html"), name='product'),
    path('about-us/', TemplateView.as_view(template_name="pages/aboutus.html"), name='about'),
    path('contact-us/', contact_us, name='contact'),
    path('web-store/', TemplateView.as_view(template_name='webstore/webHome.html'), name='webstore'),
    path('cart/', TemplateView.as_view(template_name='webstore/cart.html'), name='cart'),
    path('cart-detail/', TemplateView.as_view(template_name='webstore/cartDetail.html'), name='cart-detail'),
]
