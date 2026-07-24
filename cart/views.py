from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View  # Также что за View? 
from django.http import JsonResponse, HttpResponse  # Что делают оба? 
from django.template.response import TemplateResponse
from django.contrib import messages
from django.db import transaction
from main.models import Product, ProductSize
from .models import Cart, CartItem
from .forms import AddToCartForm
import json


class CartMixin:
    def get_cart(self, request):
        if hasattr(request, "cart"):  # Что значит hasattr(request, "cart")? - есть ли у объекта request поле cart
            return request.cart  # Откуда возвращается .cart, если опять таки мы не инициализировали cart? типо cart = Cart(): MIDDLEWARE
        
        if not request.session.session_key:  # тут вроде понятно, что если человек в первый раз зашел на сайт то создаться сессия, 
            request.session.create()  #  тогда вопрос так везде будет писаться на любом проекта?

        cart, created = Cart.objects.get_or_create(
            session_key=request.session.session_key
        )

        request.session["cart_id"] = cart.id  # вот это что значит вообще непонима? 
        request.session.midified = True
        return cart
    

class CartModalView(CartMixin, View):
    def get(self, request):
        cart = self.get_cart(request)
        context = {
            "cart": cart, 
            "cart_items": cart.items.select_related(
                "product",
                "product_size__size"  # почему product_size и вообще что за product и product_size? оптимищация SQL.
            )
        }
        return TemplateResponse(request, "cart/cart_modal.html", context)


class AddToCartView(CartMixin, View):
    @transaction.atomic  # Что делает декоратор? Зачем он тут вообще? скажем так синхронизация бд
    def post(self, request, slug):
        cart = self.get_cart(request)
        product = get_object_or_404(Product, slug=slug)

        form = AddToCartForm(request.POST, product=product)

        if not form.is_valid():
            print(form.errors)
            print(request.POST)
            return JsonResponse({  # что значит JsonResponse и как он будет в дальнейшем использоваться? 
                "error": "Invalid form data",
                "errors": form.errors,
            }, status=400)
        
        size_id = form.cleaned_data.get("size_id")
        if size_id:
            product_size = get_object_or_404(
                ProductSize,
                id=size_id,
                product=product
            )
        else:
            product_size = product.product_sizes.filter(stock__gt=0).first()
            if not product_size:
                return JsonResponse({
                    "error": "No sizes available" 
                }, status=400)
            
        quantity = form.cleaned_data["quantity"]
        if product_size.stock < quantity:
            return JsonResponse({
                "error": f"Only {product_size.stock} items available"
            }, status=400)
        
        existing_item = cart.items.filter(
            product=product,
            product_size=product_size,
        ).first()

        if existing_item:
            total_quantity = existing_item.quantity + quantity
            if total_quantity > product_size.stock:
                return JsonResponse({
                    "error": f"Cannot add {quantity} item. Only {product_size.stock - existing_item.quantity} more available."
                }, status=400)

        cart_item = cart.add_product(product, product_size, quantity)

        request.session["cart_id"] = cart.id  # Тут также что это? 
        request.session.modified = True

        if request.headers.get("HX-Request"):
            return redirect("cart:cart_modal")
        else:
            return JsonResponse({  # также почему тут используется JsonResponse, а не TemplateResponse как использовали в main приложении? 
                "success": True,  # + где context? и на какой шаблон происходит Render? Если мы вообще указали View, а не TemplateView? 
                "total_items": cart.total_items,  # а или оно всегда будет редиректить на cart_modal, потому что HTMX запрос? 
                "message": f"{product.name} added to cart",  # Тогда что просто делает этот JsonResponse? И почему нету contxt'a? 
                "cart_item_id": cart_item.id 
            })


class UpdateCartItemView(CartMixin, View):  # Что значит View? 
    @transaction.atomic  # что значит этот декоратор? 
    def post(self, request, item_id):
        cart = self.get_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        quantity = int(request.POST.get("quantity", 1))  # откуда берется quantity? и .get значит если нету quantity то создаст 1 по дефолту? 

        if quantity < 0:
            return JsonResponse({"error": "Invalid quantity"}, status=400)
        
        if quantity == 0:
            cart_item.delete()
        else:
            if quantity > cart_item.product_size.stock:
                return JsonResponse({
                    "error": f"Only {cart_item.product_size.stock} items available"
                }, status=400)

            cart_item.quantity = quantity
            cart_item.save()

        request.session["cart_id"] = cart.id
        request.session.modified = True

        context = {
            "cart": cart,
            "cart_items": cart.items.select_related(  # что за функция selected_related? и не понимаю, что за _items? Все вспомнил это обращение к 
                "product",                              # к artItem по ralated_name, тогда что такое selected_related()? 
                "product_size__size"                    # что значит двойное подчеркивание? 
            ).order_by("-added_at")  # что значит -? 
        }
        return TemplateResponse(request, "cart/cart_modal.html", context)
    

class RemoveCartItemView(CartMixin, View): 
    def post(self, request, item_id):
        cart = self.get_cart(request)

        try: 
            cart_item = cart.items.get(id=item_id)  # Почему тут так а в Update через get_object_or_404? 
            cart_item.delete()  # + почему мы используем .delete(), а не remove_item, который мы прописывали в модели
                                # почему в AddCartItem мы использовали add_product, а в Update и Remove не использовали методы из модели? 
            request.session["cart_id"] = cart.id
            request.session.modified = True
             
            context = {
                "cart": cart,
                "cart_items": cart.items.select_related(
                    "product",
                    "product_size__size",
                ).order_by("-added_at")
            }
            return TemplateResponse(request, "cart/cart_modal.html", context)
        except CartItem.DoesNotExist:
            return JsonResponse({
                "error": "Item not found"
            }, status=400)
        

class CartCountView(CartMixin, View):
    def get(self, request):
        cart = self.get_cart(request)
        return JsonResponse({  # То есть это используется в качестве своеобразного context, то есть в шаблоне мы потом тоже 
            "total_items": cart.total_items,  # сможем использовать эти переменные? Только тогда почему мы шаблон не указали? 
            "subtotal": float(cart.subtotal),  
        })
    

class ClearCartView(CartMixin, View):
    def post(self, request):
        cart = self.get_cart(request)
        cart.clear()

        request.session["cart_id"] = cart.id # также до сих пор хз что это, точнее я понимаю, что это условно сохранение какое-то в сессии 
        request.session.modified = True # просто я не понимаю как оно работает под капотом, поэтому ответь 

        if request.headers.get("HX-Request"):
            return TemplateResponse(request, "cart/cart_empty.html", {"cart": cart})
        return JsonResponse({
            "success": True,
            "message": "Cart cleared"
        })
    

class CartSummaryView(CartMixin, View):
    def get(self, request):
        cart = self.get_cart(request)
        context = {
            "cart": cart, 
            "cart_item": cart.item.select_related(
                "product",
                "product_size__size"
            ).order_by("-added_at")
        }
        return TemplateResponse(request, "cart/cart_summary.html", context)

# Почему где то return JsonResponse, а где то TemplateResponse? 