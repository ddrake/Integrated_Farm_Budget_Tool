"""
Note: Views for which the 'Dashboard' link should appear in the top nav must ensure
that farmyear_id is in the context.
"""
import datetime
import json
import csv
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic import DetailView, ListView, TemplateView
from django.views import View
from django.urls import reverse, reverse_lazy
from .models.farm_year import FarmYear
from .models.farm_crop import FarmCrop, FarmBudgetCrop
from .models.market_crop import MarketCrop, Contract
from .models.fsa_crop import FsaCrop
from .models.budget_table import BudgetManager
from .models.budget_pdf import BudgetPdf
from .models.sens_table import SensTableGroup
from .models.sens_pdf import SensPdf
from .models.contract_pdf import ContractPdf
from .models.replicate_farmyear import Replicate
from ext.models import County, Budget
from .forms import (FarmYearCreateForm, FarmYearUpdateForm, FarmYearUpdateFormForTitle,
                    FarmCropUpdateForm, FarmBudgetCropUpdateForm,
                    ZeroAcreFarmBudgetCropUpdateForm, MarketCropUpdateForm,
                    FsaCropUpdateForm, ContractCreateForm, ContractUpdateForm)
from .models.util import has_farm_years, get_current_year


class IndexView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'main/index.html',
                      {'has_farm_years': has_farm_years(request.user)})


class PrivacyView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'main/privacy.html',
                      {'has_farm_years': has_farm_years(request.user),
                       'farmyear_id': kwargs.get('farmyear', '')})


class TermsView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'main/terms.html',
                      {'has_farm_years': has_farm_years(request.user),
                       'farmyear_id': kwargs.get('farmyear', '')})


class StatusView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'main/status.html',
                      {'has_farm_years': has_farm_years(request.user),
                       'farmyear_id': kwargs.get('farmyear', '')})


class BudgetSourcesView(ListView):
    template_name = 'main/budget_sources.html'

    def get_queryset(self):
        return Budget.objects.filter(crop_year=get_current_year())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_farm_years'] = True
        context['farmyear_id'] = context['view'].kwargs['farmyear']
        context['has_prevyr_based'] = any(
            (bd.is_prevyr_based for bd in context['budget_list']))
        print(f"{context['has_prevyr_based']=}")
        return context


# -----------------------
# Farm Year related views
# -----------------------
class FarmYearsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        farm_years = FarmYear.objects.filter(user=request.user.id).all()
        return render(request, 'main/farmyears.html',
                      {'farm_years': farm_years,
                       'has_farm_years': has_farm_years(request.user)})


class FarmYearDashboard(UserPassesTestMixin, DetailView):
    model = FarmYear
    template_name = 'main/dashboard.html'

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.user

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.kwargs.get('pk', None)
        context['has_farm_years'] = True
        return context


class FarmYearCreateView(LoginRequiredMixin, CreateView):
    model = FarmYear
    form_class = FarmYearCreateForm
    template_name = 'main/farmyear_form.html'

    def get_success_url(self):
        return reverse('farmyears')

    def get_initial(self):
        return {'user': self.request.user}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = context['view'].request.user
        hasfarmyears = has_farm_years(user)
        context['has_farm_years'] = hasfarmyears
        return context


class FarmYearDeleteView(UserPassesTestMixin, DeleteView):
    model = FarmYear
    success_url = reverse_lazy('farmyears')

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = context['view'].request.user
        hasfarmyears = has_farm_years(user)
        context['has_farm_years'] = hasfarmyears
        return context


class FarmYearUpdateView(UserPassesTestMixin, UpdateView):
    form_class = FarmYearUpdateForm
    model = FarmYear
    template_name = 'main/farmyear_update_form.html'

    def test_func(self):
        fy = self.get_object()
        return self.request.user == fy.user

    def get_success_url(self):
        return reverse_lazy('farmyear_detail', args=[self.get_object().pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().pk
        context['has_farm_years'] = True
        return context


class FarmYearUpdateViewFromTitle(FarmYearUpdateView):
    form_class = FarmYearUpdateFormForTitle
    template_name = 'main/farmyear_update_form_ft.html'

    def get_success_url(self):
        return reverse_lazy('fsacrop_list', args=[self.get_object().pk])


class FarmYearDetailView(UserPassesTestMixin, DetailView):
    model = FarmYear

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = context['object'].pk
        context['has_farm_years'] = True
        return context


class GetCountyView(View):
    def get(self, request, state_id, *args, **kwargs):
        counties = County.code_and_name_for_state_id(state_id)
        return JsonResponse({'data': counties})


# ----------------------
# ListViews for FarmYear
# ----------------------
class FarmYearFarmCropListView(UserPassesTestMixin, ListView):
    template_name = 'main/farmcrops_for_farmyear.html'

    def test_func(self):
        farmyear = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farmyear.user

    def get_queryset(self):
        return FarmCrop.objects.filter(
            farm_year=self.kwargs.get('farmyear', None))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.kwargs['farmyear']
        context['has_farm_years'] = True
        return context


class FarmYearFarmBudgetCropListView(UserPassesTestMixin, ListView):
    template_name = 'main/farmbudgetcrops_for_farmyear.html'

    def test_func(self):
        farmyear = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farmyear.user

    def get_queryset(self):
        return FarmBudgetCrop.objects.filter(
            farm_year=self.kwargs.get('farmyear', None))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear'] = context['farmyear_id'] = self.kwargs.get('farmyear', None)
        context['has_farm_years'] = True
        return context


class FarmYearMarketCropListView(UserPassesTestMixin, ListView):
    template_name = 'main/marketcrops_for_farmyear.html'

    def test_func(self):
        farmyear = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farmyear.user

    def get_queryset(self):
        return MarketCrop.objects.filter(farm_year=self.kwargs.get('farmyear', None))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mc_priceinfo_list'] = [
            {'marketcrop': mc, 'priceinfo': mc.harvest_futures_price_info()}
            for mc in context['marketcrop_list']]
        context['farmyear_id'] = self.kwargs['farmyear']
        context['has_farm_years'] = True
        return context


class FarmYearFsaCropListView(UserPassesTestMixin, ListView):
    template_name = 'main/fsacrops_for_farmyear.html'

    def test_func(self):
        farmyear = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farmyear.user

    def get_queryset(self):
        farmyear = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return FsaCrop.objects.filter(farm_year=farmyear)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.kwargs.get('farmyear', None)
        context['has_farm_years'] = True
        return context


# ------------
# Update views
# ------------
class FarmCropUpdateView(UserPassesTestMixin, UpdateView):
    model = FarmCrop
    form_class = FarmCropUpdateForm

    def test_func(self):
        user = self.get_object().farm_year.user
        return self.request.user == user

    def get_success_url(self):
        return reverse_lazy('farmcrop_list', args=[self.get_object().farm_year_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().farm_year_id
        context['has_farm_years'] = True
        return context


class FarmBudgetCropUpdateView(UserPassesTestMixin, UpdateView):
    model = FarmBudgetCrop

    def test_func(self):
        user = self.get_object().farm_year.user
        return self.request.user == user

    def get_form_class(self):
        fbc = self.get_form_kwargs()['instance']
        return (ZeroAcreFarmBudgetCropUpdateForm if fbc.farm_crop.planted_acres == 0
                else FarmBudgetCropUpdateForm)

    def get_success_url(self):
        return reverse_lazy('farmbudgetcrop_list',
                            args=[self.get_object().farm_year_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().farm_year_id
        context['has_farm_years'] = True
        return context


class MarketCropUpdateView(UserPassesTestMixin, UpdateView):
    model = MarketCrop
    form_class = MarketCropUpdateForm
    template_name_suffix = "_update_form"

    def test_func(self):
        user = self.get_object().farm_year.user
        return self.request.user == user

    def get_success_url(self):
        return reverse_lazy('marketcrop_list', args=[self.get_object().farm_year_id])

    def get_context_data(self, **kwargs):
        market_crop = self.get_object()
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().farm_year_id
        context['contracts'] = market_crop.get_contracts()
        context['has_farm_years'] = True
        return context


class FsaCropUpdateView(UserPassesTestMixin, UpdateView):
    model = FsaCrop
    form_class = FsaCropUpdateForm
    template_name_suffix = "_update_form"

    def test_func(self):
        user = self.get_object().farm_year.user
        return self.request.user == user

    def get_success_url(self):
        return reverse_lazy('fsacrop_list', args=[self.get_object().farm_year_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().farm_year_id
        context['has_farm_years'] = True
        return context


# --------------------------------
# AJAX views for farm crop budgets
# --------------------------------
class FarmCropAddBudgetView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        farmcrop = int(data['farmcrop'])
        budget = int(data['budget'])
        FarmCrop.add_farm_budget_crop(farmcrop, budget)
        json_obj = json.dumps({"time": str(datetime.datetime.now()), "method": "post"})
        return HttpResponse(json_obj, 'application/json', charset='utf-8')


class FarmCropDeleteBudgetView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        farmcrop = int(data['farmcrop'])
        FarmCrop.delete_farm_budget_crop(farmcrop)
        json_obj = json.dumps({"time": str(datetime.datetime.now()), "method": "post"})
        return HttpResponse(json_obj, 'application/json', charset='utf-8')


# ----------------------
# Contract related views
# ----------------------
class MarketCropContractListView(UserPassesTestMixin, ListView):
    template_name = 'main/contracts_for_marketcrop.html'

    def test_func(self):
        mc = get_object_or_404(MarketCrop, pk=self.kwargs.get('market_crop', None))
        return self.request.user == mc.farm_year.user

    def get_queryset(self):
        mc = get_object_or_404(MarketCrop, pk=self.kwargs.get('market_crop', None))
        contracts = mc.get_contracts()
        return contracts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mc = get_object_or_404(MarketCrop, pk=self.kwargs.get('market_crop', None))
        context['marketcrop'] = mc
        context['farmyear_id'] = mc.farm_year_id
        context['has_farm_years'] = True
        context['planned_contracts'] = mc.get_planned_contracts()
        return context


class ContractCreateView(UserPassesTestMixin, CreateView):
    model = Contract
    form_class = ContractCreateForm
    template_name = 'main/contract_create_form.html'

    def test_func(self):
        mc = get_object_or_404(MarketCrop, pk=self.kwargs.get('market_crop'))
        return self.request.user == mc.farm_year.user

    def get(self, request, *args, **kwargs):
        self.extra_context = {'market_crop': kwargs['market_crop']}
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        if self.extra_context:
            return {'market_crop': self.extra_context['market_crop']}

    def get_success_url(self):
        mc_id = self.kwargs.get('market_crop', None)
        return reverse('contract_list', args=[mc_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mc_id = self.kwargs.get('market_crop', None)
        mc = get_object_or_404(MarketCrop, pk=mc_id)
        context['market_crop'] = mc
        context['farmyear_id'] = mc.farm_year_id
        context['has_farm_years'] = True
        return context


class ContractUpdateView(UserPassesTestMixin, UpdateView):
    model = Contract
    form_class = ContractUpdateForm
    template_name = "main/contract_update_form.html"

    def test_func(self):
        user = self.get_object().market_crop.farm_year.user
        return self.request.user == user

    def get_success_url(self):
        return reverse('contract_list',
                       args=[self.get_object().market_crop_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mc = self.get_object().market_crop
        context['farmyear_id'] = mc.farm_year_id
        context['has_farm_years'] = True
        return context


class ContractDeleteView(UserPassesTestMixin, DeleteView):
    model = Contract
    template_name = "main/contract_confirm_delete.html"

    def test_func(self):
        user = self.get_object().market_crop.farm_year.user
        return self.request.user == user

    def get_success_url(self):
        return reverse('contract_list',
                       args=[self.get_object().market_crop_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mc_id = context['contract'].market_crop_id
        mc = get_object_or_404(MarketCrop, pk=mc_id)
        context['farmyear_id'] = mc.farm_year_id
        context['has_farm_years'] = True
        return context


# --------------------
# Budget related views
# --------------------
class DetailedBudgetView(UserPassesTestMixin, TemplateView):
    template_name = 'main/detailed_budget.html'

    def test_func(self):
        farm_year = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farm_year.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        bm = BudgetManager(farm_year)
        budget = bm.calc_current_budget()
        context['rev'] = budget['rev']
        context['revfmt'] = budget['revfmt']
        context['info'] = budget['info']
        context['tables'] = budget['tables']
        context['keydata'] = budget['keydata']
        context['farmyear_id'] = farm_year.pk
        context['has_farm_years'] = True
        return context


class GetAjaxBudgetView(View):
    def get(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        bm = BudgetManager(farm_year)
        bdgtype = request.GET.get('bdgtype', None)
        budget = (bm.get_baseline_budget() if bdgtype == 'base' else
                  bm.get_variance_budget() if bdgtype == 'var' else
                  bm.get_current_budget())
        return JsonResponse({'data': {'rev': budget['rev'],
                                      'tables': budget['tables']}})


class BudgetPdfView(UserPassesTestMixin, View):
    """
    Expect URL of the form: downloadbudget/23/?b=1
    (b=0: current budget, b=1: baseline, b=2: variance)
    """
    def test_func(self):
        farm_year = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farm_year.user

    def get(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        budgettype = request.GET.get('b', 0)
        buffer = BudgetPdf(farm_year, budgettype).create()
        return FileResponse(buffer, as_attachment=True, filename="Budget.pdf")


class FarmYearConfirmBaselineUpdate(UserPassesTestMixin, View):
    def test_func(self):
        farm_year = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farm_year.user

    def get(self, request, *args, **kwargs):
        farm_year_id = kwargs.get('farmyear', None)
        return render(request, 'main/farmyear_confirm_baseline_update.html',
                      {'farmyear_id': farm_year_id})


class FarmYearUpdateBaselineView(UserPassesTestMixin, View):
    def test_func(self):
        farm_year = get_object_or_404(FarmYear,
                                      pk=self.request.POST.get('farmyear', None))
        return self.request.user == farm_year.user

    def post(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=request.POST.get('farmyear', None))
        farm_year.update_baseline()
        return redirect(reverse('dashboard', args=[farm_year.pk]))


# -------------------------------
# Sensitivity table related views
# -------------------------------
class SensitivityTableView(UserPassesTestMixin, TemplateView):
    template_name = 'main/sensitivity_table.html'

    def test_func(self):
        farm_year = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farm_year.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        st = SensTableGroup(farm_year)
        context['table'] = st.get_cashflow_farm()
        context['info'] = st.get_info()
        context['farmyear_id'] = farm_year.pk
        context['has_farm_years'] = True
        return context


class GetSensTableView(View):
    def get(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        st = SensTableGroup(farm_year)
        tbltype = request.GET.get('tbltype', None)
        crop = request.GET.get('crop', None)
        tblnum = request.GET.get('tblnum', '')
        tblnum = None if tblnum == '' else int(tblnum)
        isdiff = True if request.GET.get('isdiff', 'false') == 'true' else False
        print(f'{tbltype=}, {crop=}, {tblnum=}, {isdiff=}')
        table = st.get_selected_table(tbltype, crop, tblnum, isdiff)
        return JsonResponse({'data': table})


class SensitivityPdfView(UserPassesTestMixin, View):
    """
    Expect URL of the form: downloadsens/23/?tag=revenue_diff_corn
    """
    def test_func(self):
        farm_year = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farm_year.user

    def get(self, request, *args, **kwargs):
        tbltype = request.GET.get('tbltype', None)
        crop = request.GET.get('crop', None)
        tblnum = int(request.GET.get('tblnum', 0))
        isdiff = True if request.GET.get('isdiff', 'false') == 'true' else False
        nincr = int(request.GET.get('ni', 1))
        basis_incr = float(request.GET.get('bi', 0))
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        buffer = SensPdf(farm_year, isdiff).create()
        filename = get_sens_filename(tbltype, crop, tblnum, isdiff, nincr, basis_incr)
        return FileResponse(buffer, as_attachment=True, filename=filename)


# ---------------------
# Contract report views
# ---------------------
class ContractPdfView(UserPassesTestMixin, View):
    def test_func(self):
        farm_year = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farm_year.user

    def get(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        buffer = ContractPdf(farm_year).create()
        filename = "Grain Contracts.pdf"
        return FileResponse(buffer, as_attachment=True, filename=filename)


class ContractCsvView(UserPassesTestMixin, View):
    def test_func(self):
        farm_year = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farm_year.user

    def get(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition':
                     'attachment; filename="GrainContracts.csv"'},
        )
        writer = csv.writer(response)
        writer.writerow(['Crop', 'Contract Date', 'Bushels', 'Futures Price',
                         'Basis Price', 'Terminal', 'Contract #',
                         'Delivery Start', 'Delivery End'])
        for mc in farm_year.market_crops.all():
            if mc.planted_acres() > 0:
                for c in mc.get_contracts():
                    writer.writerow(
                        [mc, c.contract_date, c.bushels, c.futures_price, c.basis_price,
                         c.terminal, c.contract_number, c.delivery_start_date,
                         c.delivery_end_date])
        return response


class ReplicateView(UserPassesTestMixin, View):
    def test_func(self):
        farm_year = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return self.request.user == farm_year.user

    def get(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        user_id = kwargs.get('user', None)
        live_to_loc = request.GET.get('live_to_loc', False)
        live_to_loc = True if live_to_loc == '' else False
        r = Replicate(farm_year, user_id, live_to_loc)
        sql = r.replicate()
        response = HttpResponse(sql, headers={
            "Content-Type": "text/plain",
            "Content-Disposition": 'attachment; filename="replica.sql"',
        })
        return response


def get_sens_filename(tbltype, crop, tblnum, isdiff, nincr, basis_incr):
    """ get title info for sensitivity table pdf"""
    # Sensitivity_revenue_diff_basis_offset_0_01_fs_beans
    nst = (nincr - 1)/2
    tot_basis_incr = (basis_incr * (-nst + tblnum) if basis_incr != 0 else None)
    basis_incr_str = ('' if tot_basis_incr is None else
                      f'basis_increment_{tot_basis_incr:.2f}_')
    info = (f'{tbltype}_' + ('diff_' if isdiff else '') + basis_incr_str + crop)
    return f"Sensitivity_{info}.pdf"
