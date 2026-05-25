"""Interface admin Django."""
from django.contrib import admin
from .models import Client, Facture, ParametresHotel


@admin.register(ParametresHotel)
class ParametresHotelAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Identité', {
            'fields': ('nom', 'adresse', 'code_postal', 'ville',
                       'telephone', 'email', 'siret', 'capital')
        }),
        ('Tarifs par défaut', {
            'fields': ('tva_defaut', 'taxe_sejour_defaut', 'prix_chambre_defaut')
        }),
    )

    def has_add_permission(self, request):
        # On force une seule instance
        return not ParametresHotel.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'civilite', 'societe', 'email', 'telephone', 'cree_le')
    search_fields = ('nom', 'prenom', 'societe', 'email')
    list_filter = ('civilite',)
    ordering = ('nom', 'prenom')


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = (
        'numero_reservation', 'client', 'date_arrivee', 'date_depart',
        'statut', 'total_ttc_display'
    )
    list_filter = ('statut', 'date_arrivee')
    search_fields = ('numero_reservation', 'client__nom', 'client__prenom')
    date_hierarchy = 'date_arrivee'
    autocomplete_fields = ('client',)

    fieldsets = (
        ('Identification', {
            'fields': ('numero_reservation', 'client', 'date_edition', 'statut')
        }),
        ('Séjour', {
            'fields': ('date_arrivee', 'date_depart', 'numero_chambre',
                       'nombre_personnes', 'type_sejour')
        }),
        ('Tarification', {
            'fields': ('prix_chambre_ht', 'taux_tva', 'taxe_sejour_unitaire', 'extras')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Total TTC')
    def total_ttc_display(self, obj):
        return f'{obj.total_ttc} €'
