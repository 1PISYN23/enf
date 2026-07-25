from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
from django.template.response import TemplateResponse
from .forms import CustomUserCreationForm, CustomUserLoginFrom, CustomUserUpdateForm
from .models import CustomUser
from django.contrib import messages
from main.models import Product
from orders.models import Order


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")  # Способ авторизации пользовыателя.  
            return redirect("main:index")
    else:
        form = CustomUserCreationForm()
    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = CustomUserLoginFrom(request=request, data=request.POST)  # Почему тут в атрибутах так, а в регистрации просто request.POST? Потому что две разные формы где логин допом принимает request
        if form.is_valid():
            user = form.get_user()  # Это встроенный метод в Django, который просто берет user'a из бд? Или лучше поточнее объясни? 
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("main:index")
    else:
        form = CustomUserLoginFrom()
    return render(request, "users/login.html", {"form": form})


@login_required(login_url="/users/login")
def profile_view(request):
    if request.method == "POST":
        form = CustomUserUpdateForm(request.POST, instance=request.user)  # instance для того, чтобы загурзить инфу о пользователе? и что за request.user? откуда мы его берем? 
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                return HttpResponse(headers={"HX-Redirect": reverse("users:profile")})  # Почему HttpResponse, хотя до этого в main было постоянно TemplateResponse? И что за reverse? 
            return redirect("users:profile")  # reverse делает users/profile/. А HttpResponse отправляет заголовок для HTMX
    else:
        form = CustomUserUpdateForm(instance=request.user)

    recommended_products = Product.objects.all().order_by("id")[:3]
    orders = Order.objects.filter(user=request.user).order_by("-created_at")[:3]
    latest_order = Order.objects.last()
    
    return TemplateResponse(request, "users/profile.html", {
        "form": form,
        "user": request.user,  # был уде создан Middleware.
        "recommended_products": recommended_products,
        "orders": orders,
        "latest_order": latest_order,
    })


@login_required(login_url="/users/login")
def account_details(request):
    user = CustomUser.objects.get(id=request.user.id)
    return TemplateResponse(request, "users/partials/account_details.html", {"user": user})


@login_required(login_url="/users/login")
def edit_account_details(request):
    form = CustomUserUpdateForm(instance=request.user)
    return TemplateResponse(request, "users/partials/edit_account_details.html", {"user": request.user, "form": form})


@login_required(login_url="/users/login")
def update_account_details(request):
    if request.method == "POST":
        form = CustomUserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)  # Как мы вызываем метод save(), если его мы прописывали только в CreationForms?
            user.clean()
            user.save()
            updated_user = CustomUser.objects.get(id=user.id)
            request.user = updated_user
            if request.headers.get("HX-Request"):
                return TemplateResponse(request, "users/partials/account_details.html", {"user": updated_user})
            return TemplateResponse(request, "users/partials/account_details.html", {"user": updated_user})
        else:
            return TemplateResponse(request, "users/partials/edit_account_details.html", {"user": request.user, "form": form})
    if request.headers.get("HX-Request"):  # я так понимаю это для HTMX, то есть это без перезагрузки страницы
        return HttpResponse(headers={"HX-Redirect": reverse("users:profile")})
    return redirect("users:profile")  # а это для HTML, то есть с перезагруской страницы? И сверху также было? 


def logout_view(request):
    logout(request)
    if request.headers.get("HX-Request"):
        return HttpResponse(headers={"HX-Redirect": reverse("main:index")})
    return redirect("main:index")


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return TemplateResponse(request, "users/partials/order_history.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return TemplateResponse(request, "users/partials/order_detail.html", {"order": order})


# Из-за того, что мы делаем на HTMX, то нам надо делать допольнительно account_details да? И если бы мы делали на обычном HTML, то account_details не надо было бы делать, 
# а просто из edit_account_details сделали бы редирект на profile.html? 