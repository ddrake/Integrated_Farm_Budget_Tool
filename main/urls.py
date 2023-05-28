from django.urls import path
from .views import GetCountyView, FarmYearCreateView

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('farmyear/create', FarmYearCreateView.as_view(), name='farmyear_create'),
    path('farmyear/counties_for_state/<int:state_id>',
         GetCountyView.as_view(), name="get_counties")
]
