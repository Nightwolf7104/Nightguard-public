from django.http import HttpResponse

def login_view(request):
    return HttpResponse("<h1>Welcome to NightGuard Login Page</h1>")