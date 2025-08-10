from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from core.models import Product
from .cart import Cart
from .forms import CartAddProductForm


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product=product,
                 quantity=cd['quantity'],
                 override_quantity=cd['override'])
    return redirect('cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart_detail')


@csrf_exempt
@require_POST
def cart_update(request, product_id):
    """AJAX endpoint to update cart quantity"""
    if request.headers.get('Content-Type') == 'application/json':
        try:
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 1))

            if quantity <= 0:
                return JsonResponse({'success': False, 'error': 'Invalid quantity'})

            cart = Cart(request)
            product = get_object_or_404(Product, id=product_id)

            # Update cart with new quantity
            cart.add(product=product, quantity=quantity, override_quantity=True)

            # Calculate totals
            item_total = quantity * int(product.effective_price)
            cart_total = cart.get_total_price()
            cart_count = len(cart)

            return JsonResponse({
                'success': True,
                'item_total': item_total,
                'cart_total': cart_total,
                'cart_count': cart_count,
                'unit_price': int(product.effective_price)
            })

        except (ValueError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


def cart_detail(request):
    cart = Cart(request)
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(initial={
            'quantity': item['quantity'],
            'override': True})
    return render(request, 'cart/cart_detail.html', {'cart': cart})


def cart_count(request):
    """AJAX endpoint to get current cart count"""
    cart = Cart(request)
    return JsonResponse({
        'count': len(cart),
        'total': cart.get_total_price()
    })


@require_POST
def add_with_addons(request, product_id):
    """Add product to cart with addons"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    # Get base product data
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        base_quantity = cd['quantity']

        # Get selected addons from POST data
        selected_addons = request.POST.getlist('addons')
        addon_data = {}

        # Calculate addon costs
        addon_total = 0
        for addon_id in selected_addons:
            addon_price = request.POST.get(f'addon_price_{addon_id}')
            if addon_price:
                addon_total += int(addon_price)
                addon_data[addon_id] = int(addon_price)

        # Add product with addon information
        cart.add_with_addons(
            product=product,
            quantity=base_quantity,
            override_quantity=cd['override'],
            addons=addon_data,
            addon_total=addon_total
        )

    return redirect('cart_detail')