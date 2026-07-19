from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
from django.template.response import TemplateResponse
from .forms import CustomUserCreationForm, CustomUserLoginFrom, CustomUserUpdateForm
from .models import CustomUser
from django.contrib import messages
from main.models import Product


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")  # что за backend? Тоже объясника 
            return redirect("main:index")
    else:
        form = CustomUserCreationForm()
    return render(request, "users/register.html", {"form": form})


def login(request):
    if request.method == "POST":
        form = CustomUserLoginFrom(request=request, data=request.POST)  # Почему тут в атрибутах так, а в регистрации просто request.POST? 
        if form.is_valid():
            user = form.get_user()  # Это встроенный метод в Django, который просто берет user'a из бд? Или лучше поточнее объясни? 
            login(request, user, backend="djangp.conrib.auth.backends.ModelBackend")
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
            return redirect("users:profile")
    else:
        form = CustomUserUpdateForm(instance=request.user)

    recommended_products = Product.objects.all().order_by("id")[:3]
    
    return TemplateResponse(request, "users/profile.html", {
        "form": form,
        "user": request.user,  # почему передается request.user мы же по факту можем сделать user = CustomUser.objects.get(id=user_id) или через get_object_or_404, который укажем в url?
        "recommended_products": recommended_products
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
        return HttpResponse(headers={"HX-Redirect": reverse("user:profile")})
    return redirect("users:profile")  # а это для HTML, то есть с перезагруской страницы? И сверху также было? 


def logout_view(request):
    logout(request)
    if request.headers.get("HX-Request"):
        return HttpResponse(headers={"HX-Redirect": reverse("main:index")})
    return redirect("main:index")


# Из-за того, что мы делаем на HTMX, то нам надо делать допольнительно account_details да? И если бы мы делали на обычном HTML, то account_details не надо было бы делать, 
# а просто из edit_account_details сделали бы редирект на profile.html? 