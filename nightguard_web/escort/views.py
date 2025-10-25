from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import EscortSession
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils.timezone import now
from django.http import HttpResponse

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

@login_required
def home_view(request):
    # Get the latest active escort session for the user
    active_session = EscortSession.objects.filter(
        user=request.user,
        status__in=["Requested", "Pending"]
    ).order_by('-start_time').first()

    context = {
        "active_session": active_session
    }
    return render(request, 'escort/home.html', context)

def logout_view(request):
    logout(request)
    return redirect("login")

from django.http import JsonResponse
from django.utils import timezone

@login_required
def request_escort_view(request):
    if request.method == "POST":
        # Create a new escort session
        session = EscortSession.objects.create(
            user=request.user,
            start_time=timezone.now(),
            status="Requested"
        )
        return JsonResponse({
            "status": session.status,
            "message": "Escort requested successfully!"
        })
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def panic_view(request):
    if request.method == "POST":
        # Create a panic session or update current session
        session = EscortSession.objects.create(
            user=request.user,
            start_time=timezone.now(),
            status="Panic"
        )
        # TODO: trigger notifications to campus security here

        return JsonResponse({
            "status": session.status,
            "message": "Panic alert sent!"
        })
    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt  # allows frontend JS to send POST requests
def update_location(request):
    if request.method == "POST":
        data = json.loads(request.body)
        lat = data.get("lat")
        lon = data.get("lon")

        if request.user.is_authenticated:
            session, created = EscortSession.objects.get_or_create(
                user=request.user,
                end_time=None,  # active session
                defaults={"status": "Active"}
            )
            session.location = f"{lat}, {lon}"
            session.save()

            return JsonResponse({"status": "success", "lat": lat, "lon": lon})
        else:
            return JsonResponse({"status": "unauthorized"}, status=403)
    return JsonResponse({"error": "Invalid request"}, status=400)