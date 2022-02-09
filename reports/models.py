import random

from django.db import models

# Create your models here.
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


def generate_user_verification_code():
    n = 6
    return str(random.randint(10 ** (n - 1), 10 ** n - 1))


class Reports(models.Model):
    patient_chasing_number = models.CharField(max_length=255, unique=True)
    patient_name = models.CharField(max_length=255)
    patient_phone_number = models.CharField(max_length=15)
    patient_city = models.CharField(max_length=255)
    pin_code = models.CharField(max_length=6, blank=True)
    patient_report = models.FileField(upload_to='reports/')
    created_at = models.DateTimeField(auto_now_add=True)

    # @property
    # def pin_code_str(self):
    #     pin_code = str(self.pin_code)
    #     return pin_code


@receiver(pre_save, sender=Reports)
def create_pin_code(sender, instance, **kwargs):

    instance.pin_code = generate_user_verification_code()
        # instance.save()

#
# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     instance.profile.save()
