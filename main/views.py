from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views import View
from django.urls import reverse, reverse_lazy
from .models import FarmYear
from ext.models import County
from .forms import FarmYearCreateForm


def index(request):
    return render(request, 'main/index.html')


def dashboard(request):
    farm_years = FarmYear.objects.filter(user=request.user).all()
    return render(request, 'main/dashboard.html', {'farm_years': farm_years})


class FarmYearCreateView(CreateView):
    model = FarmYear
    form_class = FarmYearCreateForm

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


class FarmYearDeleteView(DeleteView):
    model = FarmYear
    success_url = reverse_lazy('dashboard')

    def delete(request, *args, **kwargs):
        farm_year_id = int(request.POST['id'])
        fy = FarmYear.objects.get(pk=farm_year_id)
        if not request.user.is_superuser and request.user != fy.user:
            raise PermissionDenied("Only an admin can delete another user's farm.")
        super().delete(request, *args, **kwargs)


class FarmYearUpdateView(UpdateView):
    model = FarmYear
    success_url = reverse_lazy('dashboard')
    template_name_suffix = "_update_form"
    fields = ['cropland_acres_owned', 'cropland_acres_rented', 'cash_rented_acres',
              'var_rent_cap_floor_frac', 'annual_land_int_expense',
              'annual_land_principal_pmt', 'property_taxes', 'land_repairs',
              'eligible_persons_for_cap']
