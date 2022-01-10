from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView

from reports.forms import ReportSearchForm
from reports.models import Reports


class ReportSearchView(ListView):
    template_name = 'report/report_search.html'
    context_object_name = 'report'
    # form_class = ReportSearchForm
    model = Reports

    def get_queryset(self):
        patient_number = self.request.GET.get('patient_number', None)
        pin_code = self.request.GET.get('pin_code', None)
        if pin_code and patient_number:
            object_list = Reports.objects.filter(pin_code__icontains=pin_code, patient_chasing_number=patient_number)
            return object_list
