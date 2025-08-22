from django.urls import path
from django.views.generic import TemplateView
from . import views

from .views import home

urlpatterns = [
    # Original static home page
    # path('', TemplateView.as_view(template_name="pages/home.html"), name='home'),

    # Current product listing page (static content)
    path('', views.product_list, name='home'),

    # New dynamic product listing page
    path('products/', views.product_list_dynamic, name='products_dynamic'),

    # Product detail page
    path('product/<str:slug>/', views.product_detail, name='product_detail'),

    # HTMX partial for product list
    path('get/products/', views.get_product_list, name='product_name_partial'),

    # JSON API for products (for navbar dropdown)
    path('api/products/', views.get_products_json, name='products_json'),

    # Services page with products
    path('services/', views.services_view, name='service'),

    # Static pages
    path('dnatestlist/', TemplateView.as_view(template_name="pages/dnatestlist.html"), name='dnatestlist'),
    path('checkreports/', TemplateView.as_view(template_name="pages/checkreports.html"), name='checkreports'),
    path('product/', TemplateView.as_view(template_name="pages/product.html"), name='product'),
    path('about-us/', TemplateView.as_view(template_name="pages/aboutus.html"), name='about'),
    path('contact-us/', views.contact_us, name='contact'),
    path('privacy/', TemplateView.as_view(template_name="pages/privacy.html"), name='privacy'),
    path('web-store/', TemplateView.as_view(template_name='webstore/webHome.html'), name='webstore'),

    # Commented out cart URLs (uncomment when cart app is ready)
    # path('cart/', TemplateView.as_view(template_name='webstore/cart.html'), name='cart'),
    # path('cart-detail/', TemplateView.as_view(template_name='webstore/cartDetail.html'), name='cart-detail'),
]