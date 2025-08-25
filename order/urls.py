from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
  path('', TemplateView.as_view(template_name="cart/order_checkout.html"), name='order_checkout'),
  
  path('place_order/', TemplateView.as_view(template_name="cart/place_order.html"), name='place_order'),
]
