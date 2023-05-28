from django.urls import path
from django.contrib.auth.decorators import login_required

from .views import (GetCountyView, FarmYearCreateView, FarmYearDeleteView,
                    FarmYearUpdateView)

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
    path('farmyear/counties_for_state/<int:state_id>',
         login_required(GetCountyView.as_view()), name="get_counties"),
]
