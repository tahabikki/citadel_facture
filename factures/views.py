"""Vues de l'application."""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone

from .models import Facture
from .forms import FactureForm
from .pdf_generator import generer_pdf_facture


class FactureListView(ListView):
    """Liste des factures avec recherche."""
    model = Facture
    template_name = 'factures/facture_liste.html'
    context_object_name = 'factures'
    paginate_by = 20

    def get_queryset(self):
        qs = Facture.objects.select_related('client')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(numero_reservation__icontains=q) |
                Q(client__nom__icontains=q) |
                Q(client__prenom__icontains=q)
            )
        statut = self.request.GET.get('statut', '').strip()
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['statut'] = self.request.GET.get('statut', '')
        ctx['statuts'] = Facture.STATUT_CHOICES
        return ctx


def facture_create(request):
    """Création d'une facture."""
    initial = {
        'numero_reservation': Facture.prochain_numero(),
        'date_edition': timezone.localdate(),
        'taux_tva': '2.00',
        'taxe_sejour_unitaire': '0.98',
        'prix_chambre_ht': '52.96',
    }
    if request.method == 'POST':
        form = FactureForm(request.POST)
        if form.is_valid():
            facture = form.save()
            messages.success(request, f'Facture n°{facture.numero_reservation} créée.')
            return redirect('facture_detail', pk=facture.pk)
    else:
        form = FactureForm(initial=initial)

    return render(request, 'factures/facture_form.html', {
        'form': form,
        'titre': 'Nouvelle facture',
    })


def facture_update(request, pk):
    """Édition d'une facture."""
    facture = get_object_or_404(Facture, pk=pk)
    if request.method == 'POST':
        form = FactureForm(request.POST, instance=facture)
        if form.is_valid():
            form.save()
            messages.success(request, 'Facture mise à jour.')
            return redirect('facture_detail', pk=facture.pk)
    else:
        form = FactureForm(instance=facture)

    return render(request, 'factures/facture_form.html', {
        'form': form,
        'facture': facture,
        'titre': f'Modifier facture n°{facture.numero_reservation}',
    })


def facture_detail(request, pk):
    """Détail d'une facture (aperçu HTML)."""
    facture = get_object_or_404(Facture, pk=pk)
    return render(request, 'factures/facture_detail.html', {
        'facture': facture,
    })


def facture_delete(request, pk):
    """Suppression."""
    facture = get_object_or_404(Facture, pk=pk)
    if request.method == 'POST':
        num = facture.numero_reservation
        facture.delete()
        messages.success(request, f'Facture n°{num} supprimée.')
        return redirect('facture_liste')
    return render(request, 'factures/facture_confirm_delete.html', {
        'facture': facture,
    })


def facture_pdf(request, pk):
    """Génération PDF."""
    facture = get_object_or_404(Facture, pk=pk)
    pdf_bytes = generer_pdf_facture(facture)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f'Facture_{facture.numero_reservation}_{facture.client.nom}.pdf'
    # 'inline' = affiche dans le navigateur, 'attachment' = télécharge
    disposition = request.GET.get('disposition', 'inline')
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response
