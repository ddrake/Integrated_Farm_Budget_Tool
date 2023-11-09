from django.urls import path
from . import views


urlpatterns = [
    path('posts/', views.PostsView.as_view(), name='posts'),
    path('post/<int:pk>/', views.PostDetailView.as_view(), name='post'),
    path('post/<int:pk>/<slug:slug>/', views.PostDetailView.as_view(), name='post'),
]
