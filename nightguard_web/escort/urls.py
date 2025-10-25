from django.urls import path
from .views import login_view, register_view, home_view, logout_view, update_location, request_escort_view, panic_view
from . import views

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path('home/', home_view, name='home'),
    path('logout/', logout_view, name='logout'),
    path("request-escort/", request_escort_view, name="request_escort"),
    path("panic/", panic_view, name="panic"),
    path("update_location/", update_location, name="update_location"),
]
