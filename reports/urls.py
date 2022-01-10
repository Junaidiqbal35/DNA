
from django.urls import path, include
from .views import ReportSearchView
app_name = 'reports'
urlpatterns = [

    path('check/', ReportSearchView.as_view(), name='report')

]