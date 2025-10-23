from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, authenticate

def login_view(request):
    form = AuthenticationForm(data=request.POST or None)
    message = None

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
        else:
            message = "Invalid username or password"

    return render(request, "escort/login.html", {"form": form, "message": message})

def register_view(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("login")
    return render(request, "escort/register.html", {"form": form})

def home_view(request):
    return render(request, 'escort/home.html')

from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect("login")