"""URLs de l'app factures."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.FactureListView.as_view(), name='facture_liste'),
    path('clients/', views.ClientListView.as_view(), name='clients_liste'),
    path('facture/nouvelle/', views.facture_create, name='facture_create'),
    path('facture/<int:pk>/', views.facture_detail, name='facture_detail'),
    path('facture/<int:pk>/modifier/', views.facture_update, name='facture_update'),
    path('facture/<int:pk>/supprimer/', views.facture_delete, name='facture_delete'),
    path('facture/<int:pk>/pdf/', views.facture_pdf, name='facture_pdf'),
]
