"""
Note: Views for which the 'Dashboard' link should appear in the top nav must ensure
that farmyear_id is in the context.
"""
import datetime
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic import DetailView, ListView, TemplateView
from django.views import View
from django.urls import reverse, reverse_lazy
from .models.farm_year import FarmYear
from .models.farm_crop import FarmCrop
from .models.farm_budget_crop import FarmBudgetCrop
from .models.market_crop import MarketCrop, Contract
from .models.fsa_crop import FsaCrop
from .models.budget_table import BudgetManager
from .models.budget_pdf import BudgetPdf
from .models.sens_table import SensTableGroup
from .models.sens_pdf import SensPdf
from ext.models import County
from .forms import (FarmYearCreateForm, FarmYearUpdateForm, FarmCropUpdateForm,
                    FarmBudgetCropUpdateForm, ZeroAcreFarmBudgetCropUpdateForm,
                    MarketCropUpdateForm, ContractCreateForm)


def ensure_same_user(farm_year, request, actionmsg, objmsg):
    """ Prevent a malicious user from viewing or tampering with another user's data """
    msg = "%s: %s another user's %s is not permitted."
    if isinstance(farm_year, int):
        farm_year = get_object_or_404(FarmYear, pk=farm_year)
    if not request.user == farm_year.user:
        raise PermissionDenied(msg % (request.user.username, actionmsg, objmsg))


def index(request):
    return render(request, 'main/index.html')


def farmyears(request):
    farm_years = FarmYear.objects.filter(user=request.user).all()
    return render(request, 'main/farmyears.html', {'farm_years': farm_years})


class FarmYearDashboard(DetailView):
    model = FarmYear
    template_name = 'main/dashboard.html'

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.get_object(), request, "Viewing", "dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.kwargs.get('pk', None)
        return context


class FarmYearCreateView(CreateView):
    model = FarmYear
    form_class = FarmYearCreateForm
    template_name = 'main/farmyear_form.html'

    def get_success_url(self):
        return reverse('farmyears')

    def form_valid(self, form):
        # don't put custom logic in delete() handler do this instead
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

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.get_object(), request, "Deleting", "farm year")
        return super().get(request, *args, **kwargs)

    def delete(request, *args, **kwargs):
        farm_year_id = int(request.POST['id'])
        fy = FarmYear.objects.get(pk=farm_year_id)
        if not request.user.is_superuser and request.user != fy.user:
            raise PermissionDenied("Only an admin can delete another user's farm.")
        super().delete(request, *args, **kwargs)


class FarmYearUpdateView(UpdateView):
    form_class = FarmYearUpdateForm
    model = FarmYear
    template_name = 'main/farmyear_update_form.html'

    def get(self, request, *args, **kwargs):
        farmyear = self.get_object()
        ensure_same_user(farmyear, request, "Updating", "farm year")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        farmyear = self.get_object()
        ensure_same_user(farmyear, request, "Updating", "farm year")
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('farmyear_detail', args=[self.get_object().pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().pk
        return context


class FarmYearDetailView(DetailView):
    model = FarmYear

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.get_object(), request, "Viewing", "farm details")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = context['object'].pk
        return context


class FarmYearFarmCropListView(ListView):
    template_name = 'main/farmcrops_for_farmyear.html'

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.kwargs.get('farmyear', None), request,
                         "Viewing", "farm crops")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return FarmCrop.objects.filter(
            farm_year=self.kwargs.get('farmyear', None))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.kwargs['farmyear']
        return context


class FarmYearFarmBudgetCropListView(ListView):
    template_name = 'main/farmbudgetcrops_for_farmyear.html'

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.kwargs.get('farmyear', None), request,
                         "Viewing", "farm budget crops")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return FarmBudgetCrop.objects.filter(
            farm_year=self.kwargs.get('farmyear', None))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear'] = context['farmyear_id'] = self.kwargs.get('farmyear', None)
        return context


class FarmYearMarketCropListView(ListView):
    template_name = 'main/marketcrops_for_farmyear.html'

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.kwargs.get('farmyear', None), request,
                         "Viewing", "market crops")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return MarketCrop.objects.filter(farm_year=self.kwargs.get('farmyear', None))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mc_priceinfo_list'] = [
            {'marketcrop': mc, 'priceinfo': mc.harvest_futures_price_info()}
            for mc in context['marketcrop_list']]
        context['farmyear_id'] = self.kwargs['farmyear']
        return context


class FarmYearFsaCropListView(ListView):
    template_name = 'main/fsacrops_for_farmyear.html'

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.kwargs.get('farmyear', None), request,
                         "Viewing", "fsa crops")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        farmyear = get_object_or_404(FarmYear, pk=self.kwargs.get('farmyear', None))
        return FsaCrop.objects.filter(farm_year=farmyear)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.kwargs.get('farmyear', None)
        return context


class FarmCropUpdateView(UpdateView):
    model = FarmCrop
    form_class = FarmCropUpdateForm

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.get_object().farm_year, request,
                         "Updating", "farm crops")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        ensure_same_user(self.get_object().farm_year, request, "Updating", "farm crops")
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('farmcrop_list', args=[self.get_object().farm_year_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().farm_year_id
        return context


class FarmBudgetCropUpdateView(UpdateView):
    model = FarmBudgetCrop

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.get_object().farm_year, request,
                         "Updating", "farm budget crops")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        ensure_same_user(self.get_object().farm_year, request,
                         "Updating", "farm budget crops")
        return super().post(request, *args, **kwargs)

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
        return context


class MarketCropUpdateView(UpdateView):
    model = MarketCrop
    form_class = MarketCropUpdateForm
    template_name_suffix = "_update_form"

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.get_object().farm_year, request,
                         "Updating", "market crops")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        ensure_same_user(self.get_object().farm_year, request,
                         "Updating", "market crops")
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('marketcrop_list', args=[self.get_object().farm_year_id])

    def get_context_data(self, **kwargs):
        market_crop = self.get_object()
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().farm_year_id
        context['futures_contracts'] = market_crop.get_futures_contracts()
        context['basis_contracts'] = market_crop.get_basis_contracts()
        return context


class ContractCreateView(CreateView):
    model = Contract
    form_class = ContractCreateForm
    template_name = 'main/contract_form.html'

    def dispatch(self, request, *args, **kwargs):
        print(f'in view dispatch: {kwargs=}')
        self.extra_context = {'market_crop': kwargs['market_crop'],
                              'is_basis': kwargs['is_basis']}
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        print(f'in get_initial: {self.extra_context=}')
        return {'market_crop': self.extra_context['market_crop'],
                'is_basis': 'on' if self.extra_context['is_basis'] == 1 else ''}

    def post(self, request, *args, **kwargs):
        # TODO: ensure_same_user(self.get_object().market_crop.farm_year,
        #                  request, "Creating", "contracts")
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        mc_id = self.kwargs.get('market_crop', None)
        return reverse('marketcrop_update', args=[mc_id])

    def form_valid(self, form):
        # don't put custom logic in delete() handler do this instead
        print(f'in form valid: {form.instance}')


# class ContractUpdateView(UpdateView):
#     model = Contract
#     form_class = ContractUpdateForm
#     template_name = "main/contract_form.html"

#     def get(self, request, *args, **kwargs):
#         ensure_same_user(self.get_object().farm_year, request,
#                          "Updating", "fsa crops")
#         return super().get(request, *args, **kwargs)

#     def post(self, request, *args, **kwargs):
#         ensure_same_user(self.get_object().farm_year, request,
#                          "Updating", "fsa crops")
#         return super().post(request, *args, **kwargs)

#     def get_success_url(self):
#         return reverse_lazy('fsacrop_list', args=[self.get_object().farm_year_id])


class FsaCropUpdateView(UpdateView):
    model = FsaCrop
    template_name_suffix = "_update_form"
    fields = ['plc_base_acres', 'arcco_base_acres', 'plc_yield', ]

    def get(self, request, *args, **kwargs):
        ensure_same_user(self.get_object().farm_year, request, "Updating", "fsa crops")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        ensure_same_user(self.get_object().farm_year, request, "Updating", "fsa crops")
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('fsacrop_list', args=[self.get_object().farm_year_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farmyear_id'] = self.get_object().farm_year_id
        return context


class DetailedBudgetView(TemplateView):
    template_name = 'main/detailed_budget.html'

    def get(self, request, *args, **kwargs):
        ensure_same_user(kwargs.get('farmyear', None), request, "Viewing", "budgets")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        bm = BudgetManager(farm_year)
        budgets = bm.update_budget_text()
        context['cur'] = budgets['cur']
        context['base'] = budgets['base']
        context['var'] = budgets['var']
        context['farmyear_id'] = farm_year.pk
        return context


class FarmYearConfirmBaselineUpdate(View):
    def get(self, request, *args, **kwargs):
        farm_year_id = kwargs.get('farmyear', None)
        ensure_same_user(farm_year_id, request, "Updating", "baseline budget")
        return render(request, 'main/farmyear_confirm_baseline_update.html',
                      {'farmyear_id': farm_year_id})


class FarmYearUpdateBaselineView(View):
    def post(self, request, *args, **kwargs):
        farm_year_id = request.POST.get('farmyear', None)
        farm_year = get_object_or_404(FarmYear, pk=farm_year_id)
        ensure_same_user(farm_year, request, "Updating", "baseline budget")
        farm_year.update_baseline()
        return redirect(reverse('dashboard', args=[farm_year_id]))


class BudgetPdfView(View):
    """
    Expect URL of the form: downloadbudget/23/?b=1
    (b=0: current budget, b=1: baseline, b=2: variance)
    """
    def get(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        ensure_same_user(farm_year, request, "Printing", "budget")
        budgettype = request.GET.get('b', 0)
        buffer = BudgetPdf(farm_year, budgettype).create()
        return FileResponse(buffer, as_attachment=True, filename="Budget.pdf")


class SensitivityPdfView(View):
    """
    Expect URL of the form: downloadsens/23/?tag=revenue_diff_corn
    """
    def get(self, request, *args, **kwargs):
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        ensure_same_user(farm_year, request, "Printing", "sensitivity table")
        senstype = request.GET.get('tag', 0)
        buffer = SensPdf(farm_year, senstype).create()
        filename = f"Sensitivity_{senstype}.pdf"
        return FileResponse(buffer, as_attachment=True, filename=filename)


class SensitivityTableView(TemplateView):
    template_name = 'main/sensitivity_table.html'

    def get(self, request, *args, **kwargs):
        ensure_same_user(kwargs.get('farmyear', None), request, "Viewing",
                         "sensitivity tables")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        farm_year = get_object_or_404(FarmYear, pk=kwargs.get('farmyear', None))
        st = SensTableGroup(farm_year)
        context['info'] = st.get_info()
        context['tables'] = st.get_all_tables()
        context['farmyear_id'] = farm_year.pk
        return context
