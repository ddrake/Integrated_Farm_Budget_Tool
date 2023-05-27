from django.shortcuts import render
from .models import FarmYear


def index(request):
    return render(request, 'main/index.html')


def dashboard(request):
    farm_years = FarmYear.objects.filter(user=request.user).all()
    return render(request, 'main/dashboard.html', {'farm_years': farm_years})
