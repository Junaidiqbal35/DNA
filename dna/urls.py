from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('cms/', include(wagtailadmin_urls)),
                  path('wagtail/', include(wagtail_urls)),
                  path('', include('core.urls')),
                  path('report/', include('reports.urls'))
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
