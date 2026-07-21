from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.template.response import TemplateResponse
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json 
import stripe 
import requests
import hashlib
import base64
from cart.views import CartMixin
from orders.models import Order
from decimal import Decimal


# stripe listen --forward-to localhost:8000/payment/stripe/webhook/


stripe.api_key = settings.STRIPE_SECRET_KEY
stripe_endpoint_secret = settings.STRIPE_WEBHOOK_SECRET


def create_stripe_checkout_session(order, request):
    cart = CartMixin.get_cart(request)
    line_items = []
    for item in cart.items.select_related("product", "product_size"):
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"{item.product.name} - {item.product_size.size.name}",
                },
                "unit_amount": int(item.product.size * 100),
            },
            "quantity": item.quantity,
        })
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_data=["card"],
            line_items=line_items,
            mode="payment",
            success_url=request.build_absolute_uri("/payment/stripe/success/") + "?session_id={CHECKOUT_SESSION_ID}",  # Это что за конструкция? Встроенная? 
            cancel_url=request.build_absolute_uri("/payment/stripe/cancel/") + f"order_id={order.id}",  # Это что за конструкция? Встроенная? 
            metadata={
                "order_id": order.id,
            }
        )
        order.stripe_payment_intend_id = checkout_session.payment_intent
        order.payment_provider = "stripe"
        order.save()
        return checkout_session
    except Exception as e:
        raise


@csrf_exempt
@require_POST
def stripe_webhook(request):  # WEBHOOK нужен для того чтобы понять оплатил пользователь заказ или нет; КОРОЧЕ ОБЪЯСНИТЬ ВЕСЬ МЕТОД.
    payload = request.body  
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_endpoint_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session["metadata"].get("order_id")
        try:
            order = Order.objects.get(id=order_id)
            order.status = "processing"
            order.stripe_payment_intend_id = session.get("payment_intent")
            order.save()
        except Order.DoesNotExist:
            return HttpResponse(status=400)
        
    return HttpResponse(status=200)


def stripe_success(request):
    session_id = request.GET.get("session_id")  # Это просто сессия пользователя, которая создается через Middleware?
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            order_id = session.metadata.get("order_id")
            order = get_object_or_404(Order, id=order_id)

            cart = CartMixin.get_cart(request)
            cart.clear()

            context = {"order": order}
            if request.headers.get("HX-Request"):
                return TemplateResponse(request, "payment/stripe_success_content.html", context)
            return render(request, "payment/stripe_success", context)
        except Exception as e:
            raise
    return redirect("main:index")


def stripe_cancel(request):
    order_id = request.GET.get("order_id")  # Вопрос почему тут через request, а в success через session? И где создается order_id в запросе?
    if order_id:
        order = get_object_or_404(Order, id=order_id)
        order.status = "cancelled"  # Почему в success не указывали что успешно? 
        order.save()
        context = {"order": order}
        if request.headers.get("HX-Request"):
            return TemplateResponse(request, "payment/stripe_cancel_content.html", context)  # почему тут два разных шаблона?
        return render(request, "payment/stripe_cancel.html", context)
    return redirect("orders:checkout")