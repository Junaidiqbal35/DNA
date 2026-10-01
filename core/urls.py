from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services_view, name='services'),

    path('partners/', views.partners_view, name='partners'),

    path('about/', views.about_view, name='about'),

    path('contact/', views.contact_us, name='contact'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    path('disclaimer/', TemplateView.as_view(template_name='pages/disclaimer.html'), name='disclaimer'),
    path('privacy/',    TemplateView.as_view(template_name='pages/privacy.html'),    name='privacy'),
]
