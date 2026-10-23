from django.urls import path
from . import views

app_name = 'documents'
urlpatterns = [
    path('', views.index, name='index'),
    path('templates/', views.template_list, name='template_list'),
    path('templates/new/', views.template_form, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_form, name='template_edit'),
    path('documents/<uuid:pk>/', views.detail, name='detail'),
    path('documents/<uuid:pk>/review/', views.review, name='review'),
    path('documents/<uuid:pk>/retry/', views.retry, name='retry'),
    path('documents/<uuid:pk>/delete/', views.delete, name='delete'),
    path('documents/<uuid:pk>/original/', views.original, name='original'),
    path('documents/<uuid:pk>/status/', views.status, name='status'),
    path('documents/<uuid:pk>/export/json/', views.export_json, name='export_json'),
    path('documents/<uuid:pk>/export/xlsx/', views.export_xlsx, name='export_xlsx'),
]
