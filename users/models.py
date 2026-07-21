from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager  # сразу вопрос что делают для и для чего используются? 
from django.utils.html import strip_tags  # также что делает и для чего? 


class CustomUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set.")
        email = self.normalize_email(email)  # Приводит в рабочее состояние.
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
    

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, first_name, last_name, password, **extra_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, max_length=254)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company = models.CharField(max_length=100, blank=True, null=True)
    address1 = models.CharField(max_length=255, blank=True, null=True)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)

    username = CustomUserManager()  # заменяет objects для создания новой логики авторизации, то есть у нас авторизация идет по email, а не по username и поэтому мы переопределили два метода в CustomUserManager
    # то есть если бы надо было входить по username, то мы бы могли вообще не создавать CustomUserManager

    USERNAME_FIELD = 'email'  # выполнять вход по email а не по username
    REQUIRED_FIELDS = ['first_name', 'last_name']  # обязательны команды для createsuperuser

    
    def __str__(self):
        return self.email
    

    def clean(self):   # встроенный метод django, нужен для доп. валидации 
        for field in ['company', 'address1', 'address2', 'city',
                      'country', 'province', 'postal_code', 'phone']:
            value = getattr(self, field)
            if value:
                setattr(self, field, strip_tags(value))  # убирает весь HTML :<b>Hello</b> -> Hello, Нужен в тех полях, где пользователь может ввести HTML 