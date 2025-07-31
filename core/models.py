from django.db import models
from django.urls import reverse
from ckeditor.fields import RichTextField


# Create your models here.
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d',
                              blank=True)
    description = RichTextField(blank=True)
    price = models.PositiveBigIntegerField()
    discounted_price = models.PositiveBigIntegerField(blank=True, null=True)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['name']),
            models.Index(fields=['-created']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:product_detail',
                       args=[self.slug])

    @property
    def discount_amount(self):
        """Calculate the discount amount if discounted_price exists"""
        if self.discounted_price and self.discounted_price < self.price:
            return self.price - self.discounted_price
        return 0

    @property
    def discount_percentage(self):
        """Calculate the discount percentage"""
        if self.discounted_price and self.discounted_price < self.price:
            return round(((self.price - self.discounted_price) / self.price) * 100)
        return 0

    @property
    def effective_price(self):
        """Return the effective price (discounted if available, otherwise regular price)"""
        return self.discounted_price if self.discounted_price else self.price


class Contact(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    message = models.TextField()
    phone_number = models.CharField(max_length=15)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.name