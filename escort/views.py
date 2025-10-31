from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
import json
from .models import EscortSession
from zoneinfo import ZoneInfo
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
    
def get_address_from_coords(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        response = requests.get(url, headers={"User-Agent": "NightGuardApp"})
        data = response.json()
        return data.get("display_name", "Address not available")
    except Exception:
        return "Address not available"

# PANIC
@login_required
def panic_view(request):
    if request.method == "POST":
        # Create a panic session
        session = EscortSession.objects.create(
            user=request.user,
            start_time=timezone.now(),
            status="Panic"
        )

        # Get latest known location if available
        latest_session = EscortSession.objects.filter(
            user=request.user
        ).exclude(location__isnull=True).order_by('-start_time').first()

        # Extract coordinates and get readable address
        if latest_session and latest_session.location:
            try:
                lat, lon = latest_session.location.split(",")
                address = get_address_from_coords(lat.strip(), lon.strip())
                map_link = f"https://www.google.com/maps/search/?api=1&query={lat.strip()},{lon.strip()}"
            except Exception:
                address = "Location unavailable"
                map_link = ""
        else:
            address = "Not available"
            map_link = ""

        # Email alert details
        subject = f" Panic Alert - {request.user.username}"
        
        message = (
            f"PANIC ALERT TRIGGERED \n\n"
            f"User: {request.user.username}\n"
            f"Time: {timezone.now().astimezone(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Location: {address}\n"
            + (f"Google Map Link: {map_link}\n\n" if map_link else "\n")
            + "This alert was automatically sent by NightGuard.""\n"
            +f"Message ID: {timezone.now().timestamp()}"

        )

        recipients = [
            "akhilsaraswatula@my.unt.edu",
            "saadsyed@my.unt.edu",
            "alinaruhi@my.unt.edu",
            "joshuacharles@my.unt.edu"
            
        ]

        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients)
            return JsonResponse({
                "status": "Panic",
                "message": " Panic alert email sent successfully"
            })
        except Exception as e:
            return JsonResponse({
                "status": "Error",
                "message": f" Failed to send email: {str(e)}"
            }, status=500)

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

# END ROUTE
@login_required
def end_route(request, session_id):
    if request.method == "POST":
        try:
            session = EscortSession.objects.get(id=session_id, user=request.user)
            session.status = "Completed"
            session.end_time = timezone.now()
            session.save()
            return redirect("home")  # Go back to home after ending
        except EscortSession.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)

    return JsonResponse({"error": "Invalid request method"}, status=405)