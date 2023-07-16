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
from .models.budget_table import BudgetTable, RevenueDetails
from .models.sens_table import SensTable
from .models.key_data import KeyData
from ext.models import County
from .forms import (FarmYearCreateForm, FarmYearUpdateForm, FarmCropUpdateForm,
                    FarmBudgetCropUpdateForm, ZeroAcreFarmBudgetCropUpdateForm)


def index(request):
    return render(request, 'main/index.html')


def farmyears(request):
    farm_years = FarmYear.objects.filter(user=request.user).all()
    return render(request, 'main/farmyears.html', {'farm_years': farm_years})


class FarmYearDashboard(DetailView):
    model = FarmYear
    template_name = 'main/dashboard.html'


class FarmYearCreateView(CreateView):
    model = FarmYear
    form_class = FarmYearCreateForm

    def get_success_url(self):
        return reverse('farmyears')

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


class FarmCropDeleteBudgetView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        farmcrop = int(data['farmcrop'])
        FarmCrop.delete_farm_budget_crop(farmcrop)
        json_obj = json.dumps({"time": str(datetime.datetime.now()), "method": "post"})
        return HttpResponse(json_obj, 'application/json', charset='utf-8')


class FarmYearDeleteView(DeleteView):
    model = FarmYear
    success_url = reverse_lazy('farmyears')

    def delete(request, *args, **kwargs):
        farm_year_id = int(request.POST['id'])
        fy = FarmYear.objects.get(pk=farm_year_id)
        if not request.user.is_superuser and request.user != fy.user:
            raise PermissionDenied("Only an admin can delete another user's farm.")
        super().delete(request, *args, **kwargs)


class FarmYearUpdateView(UpdateView):
    form_class = FarmYearUpdateForm
    model = FarmYear

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear'] = self.kwargs['farmyear']
        return context


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

    def get_form_class(self):
        fbc = self.get_form_kwargs()['instance']
        return (ZeroAcreFarmBudgetCropUpdateForm if fbc.farm_crop.planted_acres == 0
                else FarmBudgetCropUpdateForm)

    def get_success_url(self):
        return reverse_lazy('farmbudgetcrop_list',
                            args=[self.get_object().farm_year_id])


class MarketCropUpdateView(UpdateView):
    model = MarketCrop
    template_name_suffix = "_update_form"
    fields = ['contracted_bu', 'avg_contract_price', 'basis_bu_locked',
              'avg_locked_basis', 'assumed_basis_for_new', 'price_factor', ]

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
        rd = RevenueDetails(farmyear)
        kd = KeyData(farmyear)
        context['rev'] = rd.get_rows()
        context['revfmt'] = rd.get_formats()
        context['info'] = bt.get_info()
        context['tables'] = bt.get_tables()
        context['keydata'] = kd.get_tables()
        return context


class SensitivityTableView(TemplateView):
    template_name = 'main/sensitivity_table.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        farmyear = kwargs.get('farmyear', None)
        st = SensTable(farmyear)
        kd = KeyData(farmyear, for_sens_table=True)
        context['info'] = st.get_info()
        context['tables'] = st.get_all_tables()
        context['keydata'] = kd.get_tables()
        return context
