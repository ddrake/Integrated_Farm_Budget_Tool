from django.urls import path
from django.contrib.auth.decorators import login_required

from .views import (GetCountyView, FarmYearCreateView, FarmYearDeleteView,
                    FarmYearUpdateView, FarmYearDetailView, FarmYearFarmCropListView,
                    FarmYearMarketCropListView, FarmYearFsaCropListView,
                    FarmCropUpdateView, MarketCropUpdateView, FsaCropUpdateView)

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', login_required(views.dashboard), name='dashboard'),
    path('farmyear/create', login_required(FarmYearCreateView.as_view()),
         name='farmyear_create'),
    path('farmyear/update/<int:pk>', login_required(FarmYearUpdateView.as_view()),
         name='farmyear_update'),
    path('farmyear/delete/<int:pk>', login_required(FarmYearDeleteView.as_view()),
         name='farmyear_delete'),
    path('farmyear/<int:pk>', login_required(FarmYearDetailView.as_view()),
         name='farmyear_detail'),
    path('farmyear/counties_for_state/<int:state_id>',
         login_required(GetCountyView.as_view()), name="get_counties"),
    path('farmcrops/<int:farmyear>', login_required(FarmYearFarmCropListView.as_view()),
         name='farmcrop_list'),
    path('farmcrop/update/<int:pk>', login_required(FarmCropUpdateView.as_view()),
         name='farmcrop_update'),
    path('marketcrops/<int:farmyear>',
         login_required(FarmYearMarketCropListView.as_view()), name='marketcrop_list'),
    path('marketcrop/update/<int:pk>', login_required(MarketCropUpdateView.as_view()),
         name='marketcrop_update'),
    path('fsacrops/<int:farmyear>', login_required(FarmYearFsaCropListView.as_view()),
         name='fsacrop_list'),
    path('fsacrop/update/<int:pk>', login_required(FsaCropUpdateView.as_view()),
         name='fsacrop_update'),
]
