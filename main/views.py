import json
import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic import DetailView, ListView, TemplateView
from django.views import View
from django.urls import reverse, reverse_lazy
from .models.farm_year import FarmYear
from .models.farm_crop import FarmCrop
from .models.farm_budget_crop import FarmBudgetCrop
from .models.market_crop import MarketCrop
from .models.fsa_crop import FsaCrop
from .models.budget_table import BudgetTable
from ext.models import County
from .forms import FarmYearCreateForm, FarmCropUpdateForm


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
        counties = County.code_and_name_for_state_id(state_id)
        return JsonResponse({'data': counties})


class FarmCropAddBudgetView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        farmcrop = int(data['farmcrop'])
        budget = int(data['budget'])
        FarmCrop.add_farm_budget_crop(farmcrop, budget)
        json_obj = json.dumps({"time": str(datetime.datetime.now()), "method": "post"})
        return HttpResponse(json_obj, 'application/json', charset='utf-8')


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
    template_name_suffix = "_update_form"
    fields = ['cropland_acres_owned', 'cropland_acres_rented', 'cash_rented_acres',
              'var_rent_cap_floor_frac', 'annual_land_int_expense',
              'annual_land_principal_pmt', 'property_taxes', 'land_repairs',
              'eligible_persons_for_cap', 'other_nongrain_income',
              'other_nongrain_expense', 'price_factor', 'yield_factor',
              'report_type', 'model_run_date', 'is_model_run_date_manual']

    def get_success_url(self):
        return reverse_lazy('farmyear_detail', args=[self.get_object().pk])


class FarmYearDetailView(DetailView):
    model = FarmYear


class FarmYearFarmCropListView(ListView):
    template_name = 'main/farmcrops_for_farmyear.html'

    def get_queryset(self):
        self.farmyear = get_object_or_404(FarmYear, pk=self.kwargs['farmyear'])
        return FarmCrop.objects.filter(farm_year=self.farmyear)


class FarmYearFarmBudgetCropListView(ListView):
    template_name = 'main/farmbudgetcrops_for_farmyear.html'

    def get_queryset(self):
        self.farmyear = get_object_or_404(FarmYear, pk=self.kwargs['farmyear'])
        return FarmBudgetCrop.objects.filter(farm_year=self.farmyear)


class FarmYearMarketCropListView(ListView):
    template_name = 'main/marketcrops_for_farmyear.html'

    def get_queryset(self):
        self.farmyear = get_object_or_404(FarmYear, pk=self.kwargs['farmyear'])
        return MarketCrop.objects.filter(farm_year=self.farmyear)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mc_priceinfo_list'] = [
            {'marketcrop': mc, 'priceinfo': mc.harvest_futures_price_info()}
            for mc in context['marketcrop_list']]
        return context


class FarmYearFsaCropListView(ListView):
    template_name = 'main/fsacrops_for_farmyear.html'

    def get_queryset(self):
        self.farmyear = get_object_or_404(FarmYear, pk=self.kwargs['farmyear'])
        return FsaCrop.objects.filter(farm_year=self.farmyear)


class FarmCropUpdateView(UpdateView):
    model = FarmCrop
    form_class = FarmCropUpdateForm

    def get_success_url(self):
        return reverse_lazy('farmcrop_list', args=[self.get_object().farm_year_id])


class FarmBudgetCropUpdateView(UpdateView):
    model = FarmBudgetCrop
    template_name_suffix = "_update_form"
    fields = ['farm_yield', 'county_yield', 'yield_variability',
              'other_gov_pmts', 'other_revenue', 'fertilizers', 'pesticides',
              'seed', 'drying', 'storage', 'other_direct_costs', 'machine_hire_lease',
              'utilities', 'machine_repair', 'fuel_and_oil', 'light_vehicle',
              'machine_depr', 'labor_and_mgmt', 'building_repair_and_rent',
              'building_depr', 'insurance', 'misc_overhead_costs', 'interest_nonland',
              'other_overhead_costs', 'rented_land_costs']

    def get_success_url(self):
        return reverse_lazy('farmbudgetcrop_list',
                            args=[self.get_object().farm_year_id])


class MarketCropUpdateView(UpdateView):
    model = MarketCrop
    template_name_suffix = "_update_form"
    fields = ['contracted_bu', 'avg_contract_price', 'basis_bu_locked',
              'avg_locked_basis', 'assumed_basis_for_new', ]

    def get_success_url(self):
        return reverse_lazy('marketcrop_list', args=[self.get_object().farm_year_id])


class FsaCropUpdateView(UpdateView):
    model = FsaCrop
    template_name_suffix = "_update_form"
    fields = ['plc_base_acres', 'arcco_base_acres', 'plc_yield', ]

    def get_success_url(self):
        return reverse_lazy('fsacrop_list', args=[self.get_object().farm_year_id])


class DetailedBudgetView(TemplateView):
    template_name = 'main/detailed_budget.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        farmyear = kwargs.get('farmyear', None)
        bt = BudgetTable(farmyear)
        context['tables'] = bt.get_tables()
        return context


class TestView(TemplateView):
    template_name = 'main/test.html'
