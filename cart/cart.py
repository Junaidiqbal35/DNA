from decimal import Decimal
from django.conf import settings
from core.models import Product


class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products
        from the database.
        """
        product_ids = self.cart.keys()
        # get the product objects and add them to the cart
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product
        for item in cart.values():
            item['price'] = int(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            # Add addon total if it exists
            if 'addon_total' in item:
                item['total_price'] += item['addon_total'] * item['quantity']
            yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def add(self, product, quantity=1, override_quantity=False):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)
        # Use effective_price (discounted price if available, otherwise regular price)
        price = product.discounted_price if product.discounted_price else product.price

        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(price)
            }
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def add_with_addons(self, product, quantity=1, override_quantity=False, addons=None, addon_total=0):
        """
        Add a product to the cart with addons.
        """
        product_id = str(product.id)
        # Use effective_price (discounted price if available, otherwise regular price)
        price = product.discounted_price if product.discounted_price else product.price

        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(price),
                'addons': addons or {},
                'addon_total': addon_total
            }
        else:
            # Update existing item
            if addons:
                self.cart[product_id]['addons'] = addons
            if addon_total:
                self.cart[product_id]['addon_total'] = addon_total

        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def save(self):
        # mark the session as "modified" to make sure it gets saved
        self.session.modified = True

    def remove(self, product):
        """
        Remove a product from the cart.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        # remove cart from session
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def get_total_price(self):
        total = 0
        for item in self.cart.values():
            base_price = int(item['price']) * item['quantity']
            addon_price = item.get('addon_total', 0) * item['quantity']
            total += base_price + addon_price
        return total