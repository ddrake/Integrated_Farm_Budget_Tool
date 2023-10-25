from django.urls import path
from django.contrib.auth.decorators import login_required

from .views import (
    IndexView, FarmYearsView, GetCountyView, FarmYearCreateView, FarmYearDashboard,
    FarmYearDetailView, FarmYearUpdateView, FarmYearUpdateViewFromTitle,
    FarmYearDeleteView,
    FarmYearFarmCropListView, FarmYearMarketCropListView, FarmYearFsaCropListView,
    FarmYearFarmBudgetCropListView,
    FarmCropUpdateView, MarketCropUpdateView, FsaCropUpdateView,
    FarmBudgetCropUpdateView,
    FarmCropAddBudgetView, FarmCropDeleteBudgetView,
    FarmYearUpdateBaselineView, FarmYearConfirmBaselineUpdate,
    DetailedBudgetView, BudgetPdfView,
    SensitivityTableView, GetSensTableView, SensitivityPdfView,
    ContractCreateView, ContractUpdateView, ContractDeleteView,
    MarketCropContractListView,
    ContractPdfView, ContractCsvView, PrivacyView, TermsView, StatusView,
    BudgetSourcesView, ReplicateView)

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('privacy/<int:farmyear>', PrivacyView.as_view(), name='privacy'),
    path('privacy/', PrivacyView.as_view(), name='privacy'),
    path('terms/<int:farmyear>', TermsView.as_view(), name='terms'),
    path('terms/', TermsView.as_view(), name='terms'),
    path('status/<int:farmyear>', StatusView.as_view(), name='status'),
    path('status/', StatusView.as_view(), name='status'),
    path('budgetsources/<int:farmyear>', BudgetSourcesView.as_view(),
         name='budgetsources'),
    path('replicate/<int:farmyear>/<int:user>', ReplicateView.as_view(),
         name='replicate'),

    # farm year related urls
    path('farmyears/', FarmYearsView.as_view(), name='farmyears'),
    path('dashboard/<int:pk>', FarmYearDashboard.as_view(),
         name='dashboard'),
    path('farmyear/<int:pk>', FarmYearDetailView.as_view(),
         name='farmyear_detail'),
    path('farmyear/create', FarmYearCreateView.as_view(),
         name='farmyear_create'),
    path('farmyear/update/<int:pk>', FarmYearUpdateView.as_view(),
         name='farmyear_update'),
    path('farmyear/update_ft/<int:pk>', FarmYearUpdateViewFromTitle.as_view(),
         name='farmyear_update_ft'),
    path('farmyear/delete/<int:pk>', FarmYearDeleteView.as_view(),
         name='farmyear_delete'),
    path('farmyear/counties_for_state/<int:state_id>',
         login_required(GetCountyView.as_view())),
    # list views for farm year
    path('farmcrops/<int:farmyear>', FarmYearFarmCropListView.as_view(),
         name='farmcrop_list'),
    path('farmbudgetcrops/<int:farmyear>', FarmYearFarmBudgetCropListView.as_view(),
         name='farmbudgetcrop_list'),
    path('marketcrops/<int:farmyear>', FarmYearMarketCropListView.as_view(),
         name='marketcrop_list'),
    path('fsacrops/<int:farmyear>', FarmYearFsaCropListView.as_view(),
         name='fsacrop_list'),

    # update views for crops
    path('farmcrop/update/<int:pk>', FarmCropUpdateView.as_view(),
         name='farmcrop_update'),
    path('farmbudgetcrop/update/<int:pk>', FarmBudgetCropUpdateView.as_view(),
         name='farmbudgetcrop_update'),
    path('marketcrop/update/<int:pk>', MarketCropUpdateView.as_view(),
         name='marketcrop_update'),
    path('fsacrop/update/<int:pk>', FsaCropUpdateView.as_view(),
         name='fsacrop_update'),

    # ajax views for crop budgets
    path('farmcrops/addbudget/', FarmCropAddBudgetView.as_view(), name='addbudget'),
    path('farmcrops/deletebudget/', FarmCropDeleteBudgetView.as_view(),
         name='deletebudget'),

    # contract related views
    path('contracts/<int:market_crop>',
         MarketCropContractListView.as_view(), name='contract_list'),

    path('contract/create/<int:market_crop>',
         ContractCreateView.as_view(), name='contract_create'),

    path('contract/update/<int:pk>',
         ContractUpdateView.as_view(), name='contract_update'),
    path('contract/delete/<int:pk>',
         ContractDeleteView.as_view(), name='contract_delete'),

    # detailed budget related views
    path('detailedbudget/<int:farmyear>',
         DetailedBudgetView.as_view(), name='detailedbudget'),
    path('downloadbudget/<int:farmyear>',
         BudgetPdfView.as_view(), name='downloadbudget'),
    path('updatebaseline/',
         FarmYearUpdateBaselineView.as_view(), name='updatebaseline'),
    path('farmyear/confirmbaseline/<int:farmyear>',
         FarmYearConfirmBaselineUpdate.as_view(),
         name='confirmbaselineupdate'),

    # sensitivity table related views
    path('sensitivity/<int:farmyear>',
         SensitivityTableView.as_view(), name='sensitivity'),
    path('sensitivity/sens_table/<int:farmyear>',
         GetSensTableView.as_view(), name='sens_table'),
    path('downloadsens/<int:farmyear>',
         SensitivityPdfView.as_view(), name='downloadsens'),

    # contract report related views
    path('downloadcontracts/<int:farmyear>',
         ContractPdfView.as_view(), name='downloadcontracts'),
    path('downloadcontracts_csv/<int:farmyear>',
         ContractCsvView.as_view(), name='downloadcontracts_csv'),
]
