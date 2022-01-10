from django.shortcuts import render

# Create your views here.


from django.views.generic import TemplateView

from core.forms import ContactForm


def home(request):
    return render(request,
                  'pages/home.html')


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
