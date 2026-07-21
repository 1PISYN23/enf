from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.utils.html import strip_tags
from django.core.validators import RegexValidator


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True, widget=forms.EmailInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "EMAIL"}))
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "FIRST NAME"}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "LAST NAME"}))
    password1 = forms.CharField(required=True, widget=forms.PasswordInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "PASSWORD"}))
    password2 = forms.CharField(required=True, widget=forms.PasswordInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "CONFIRM PASSWORD"})) 


    class Meta:  # Напомни что делает класс Meta?
        model = User
        fields = ("first_name", "last_name", "email", "password1", "password2")  # показывать только эти поля.


    def clean_email(self):  # Встроенный метод в django, когда мы делаем form.is_valid().
        email = self.cleaned_data.get("email")  # это берется очищенный email.
        if User.objects.filter(email=email).exists():  # если такой email уже существует.
            raise forms.ValidationError("This email is already in use.")
        return email
    

    def save(self, commit=True):  # Объясни что тут происходит? 
        user = super().save(commit=False)
        user.username = None
        if commit:
            user.save()
        return user
    

class CustomUserLoginFrom(AuthenticationForm):
    username = forms.CharField(label="Email", widget=forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "EMAIL"}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "PASSWORD"}))


    def clean(self):  # Вызывается автоматически когда form.is_valid()
        email = self.cleaned_data.get("username")  
        password = self.cleaned_data.get("password")  

        if email and password: 
            self.user_cache = authenticate(self.request, email=email, password=password)  # что значит это, как работает? 
            if self.user_cache is None:
                self.add_error("password", "Invalid email or password")
            elif not self.user_cache.is_active:
                raise forms.ValidationError("This account is inacive.")
        return self.cleaned_data
    

class CustomUserUpdateForm(forms.ModelForm):
    phone = forms.CharField(
        required=False,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', "Enter a valid phone number.")],
        widget=forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "PHONE NUMBER"})
    )
    first_name = forms.CharField(
        required=True,
        max_length=50,
        widget=forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "FIRST NAME"})
    )
    last_name = forms.CharField(
        required=True,
        max_length=50,
        widget=forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "LAST NAME"})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "EMAIL"})
    )


    class Meta: 
        model = User
        fields = ["first_name", "last_name", "email", "company", "address1", "address2", "city", "country", "province", "postal_code", "phone"]
        widgets = {
            "company": forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "COMPANY"}),
            "address1": forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "ADDRESS LINE 1"}),
            "address2": forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "ADDRESS LINE 2"}),
            "city": forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "CITY"}),
            "country": forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "COUNTRY"}),
            "province": forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "PROVINCE"}),
            "postal_code": forms.TextInput(attrs={"class": "dotted-input w-full py-3 text-sm font-medium text-gray-900 placeholder-gray-500", "placeholder": "POSTAL CODE"}),
        }

    
    def clean_email(self):  # если пользователь нажмет редактировать и потом ничего не меняя сохранить, то без переопределния этого метода будет ошибка.
        email = self.cleaned_data.get("email") 
        if email and User.objects.filter(email=email).exclude(id=self.instance.id).exists():  # Вот эту строчку объяснить? 
            raise forms.ValidationError("This email is already in use.")
        return email
    

    def clean(self):
        cleaned_data = super().clean()  # Почему тут через super а выше нет? 
        if not cleaned_data.get("email"):
            cleaned_data["email"] = self.instance.email  # instance = reqquest.user
        for field in ["company", "address1", "address2", "city", "country", "province", "postal_code", "phone"]:  # Почнму тут нету first_name, last_name, email? 
            if cleaned_data.get(field):
                cleaned_data[field] = strip_tags(cleaned_data[field])  # также что делает strip_tags? Что тут происходит? 
        return cleaned_data
