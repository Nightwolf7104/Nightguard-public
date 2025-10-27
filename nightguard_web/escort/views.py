from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import EscortSession
import requests

# ---------- AUTH ----------
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


def logout_view(request):
    logout(request)
    return redirect("login")


# HOME
@login_required
def home_view(request):
    active_session = EscortSession.objects.filter(
        user=request.user,
        status__in=["Requested", "Pending"]
    ).order_by('-start_time').first()

    context = {"active_session": active_session}
    return render(request, "escort/home.html", context)


# ESCORT REQUEST
@csrf_exempt
@login_required
def request_escort(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            lat = data.get("lat")
            lon = data.get("lon")
            destination = data.get("destination")  # <- Add this

            # End any ongoing session
            EscortSession.objects.filter(user=request.user, end_time__isnull=True).update(status="Completed")

            # Create new session
            session = EscortSession.objects.create(
                user=request.user,
                status="Requested",
                location=f"{lat}, {lon}",
                destination=destination   # <- Save it here
            )

            return JsonResponse({
                "message": "Escort requested successfully",
                "session_id": session.id
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)



# PANIC
@login_required
def panic_view(request):
    if request.method == "POST":
        session = EscortSession.objects.create(
            user=request.user,
            start_time=timezone.now(),
            status="Panic"
        )
        # TODO: Add alert/notification logic here
        return JsonResponse({
            "status": session.status,
            "message": "Panic alert sent!"
        })
    return JsonResponse({"error": "Invalid request"}, status=400)


# LOCATION UPDATES
@csrf_exempt
@login_required
def update_location(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            lat = data.get("lat")
            lon = data.get("lon")

            EscortSession.objects.filter(user=request.user, end_time__isnull=True).update(
                location=f"{lat}, {lon}"
            )

            return JsonResponse({"message": "Location updated"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

# ESCORT SCREEN
@login_required
def escort_view(request):
    session = EscortSession.objects.filter(user=request.user, end_time__isnull=True).order_by('-start_time').first()
    destination_coords = None
    directions_text = "Calculating route..."
    eta = "--:--"
    destination = "Unknown"

    if session and session.destination:
        destination = session.destination
        try:
            # Use Nominatim to geocode the destination
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": session.destination,
                "format": "json",
                "limit": 1
            }
            response = requests.get(url, params=params, headers={"User-Agent": "NightGuardApp"})
            data = response.json()
            if data:
                dest_lat = float(data[0]["lat"])
                dest_lon = float(data[0]["lon"])
                destination_coords = (dest_lat, dest_lon)

                # Optional: Compute ETA using OSRM API
                if session.location:
                    user_lat, user_lon = map(float, session.location.split(","))
                    route_url = f"https://router.project-osrm.org/route/v1/driving/{user_lon},{user_lat};{dest_lon},{dest_lat}?overview=false"
                    route_res = requests.get(route_url).json()
                    if route_res.get("routes"):
                        eta_seconds = route_res["routes"][0]["duration"]
                        minutes = int(eta_seconds // 60)
                        eta = f"{minutes} min"
                        directions_text = "Follow the route on the map"
        except Exception as e:
            print("Error getting destination coords:", e)
    
    context = {
        "session": session,
        "destination": destination,
        "destination_coords": destination_coords,
        "directions_text": directions_text,
        "eta": eta,
    }
    return render(request, "escort/escort.html", context)

# SETTINGS SCREEN
@login_required
def settings_view(request):
    return render(request, "escort/settings.html")
