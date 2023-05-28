from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic.edit import CreateView
from django.views import View
from django.urls import reverse
from .models import FarmYear
from ext.models import County
from .forms import FarmYearForm


def index(request):
    return render(request, 'main/index.html')


def dashboard(request):
    farm_years = FarmYear.objects.filter(user=request.user).all()
    return render(request, 'main/dashboard.html', {'farm_years': farm_years})


class FarmYearCreateView(CreateView):
    model = FarmYear
    form_class = FarmYearForm

    def get_success_url(self):
        return reverse('dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class GetCountyView(View):
    def get(self, request, state_id, *args, **kwargs):
        print("got ajax request")
        counties = County.code_and_name_for_state_id(state_id)
        print(type(counties))
        return JsonResponse({'data': counties})
