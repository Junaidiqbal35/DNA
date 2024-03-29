from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('cart/', include('cart.urls')),
                  path('order/', include('order.urls')),
                  path('', include('core.urls')),
                  path('report/', include('reports.urls')),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
