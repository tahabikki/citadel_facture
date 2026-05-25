"""Formulaires Django."""
from django import forms
from .models import Facture, Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['civilite', 'nom', 'prenom', 'email', 'telephone', 'adresse']
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 2}),
        }


class FactureForm(forms.ModelForm):
    # Champs pour saisir un client à la volée si besoin
    nouveau_client = forms.BooleanField(
        required=False, label='Créer un nouveau client',
        initial=False
    )
    civilite = forms.ChoiceField(
        choices=Client.CIVILITE_CHOICES, required=False, label='Civilité'
    )
    nom = forms.CharField(max_length=100, required=False, label='Nom')
    prenom = forms.CharField(max_length=100, required=False, label='Prénom')

    class Meta:
        model = Facture
        fields = [
            'numero_reservation', 'client',
            'date_arrivee', 'date_depart', 'date_edition',
            'numero_chambre', 'nombre_personnes', 'type_sejour',
            'prix_chambre_ht', 'taux_tva', 'taxe_sejour_unitaire', 'extras',
            'statut', 'notes',
        ]
        widgets = {
            'date_arrivee': forms.DateInput(attrs={'type': 'date'}),
            'date_depart': forms.DateInput(attrs={'type': 'date'}),
            'date_edition': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre client non-obligatoire si on coche "nouveau_client"
        self.fields['client'].required = False
        self.fields['client'].empty_label = '— Sélectionner un client —'

    def clean(self):
        cleaned = super().clean()
        nouveau = cleaned.get('nouveau_client')
        client = cleaned.get('client')

        if nouveau:
            if not cleaned.get('nom') or not cleaned.get('prenom'):
                raise forms.ValidationError(
                    'Si "Nouveau client" est coché, nom et prénom sont obligatoires.'
                )
        elif not client:
            raise forms.ValidationError(
                'Sélectionne un client existant ou coche "Nouveau client".'
            )

        # Cohérence dates
        da = cleaned.get('date_arrivee')
        dd = cleaned.get('date_depart')
        if da and dd and dd <= da:
            raise forms.ValidationError('La date de départ doit être postérieure à l\'arrivée.')

        return cleaned

    def save(self, commit=True):
        # Création du client si demandé
        if self.cleaned_data.get('nouveau_client'):
            client = Client.objects.create(
                civilite=self.cleaned_data['civilite'],
                nom=self.cleaned_data['nom'],
                prenom=self.cleaned_data['prenom'],
            )
            self.instance.client = client
        return super().save(commit=commit)
