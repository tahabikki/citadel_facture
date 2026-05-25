"""Vues de l'application."""
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone

from .models import Facture, Client
from .forms import ClientForm, FactureForm, UserSettingsForm


def pagination_context(request):
    params = request.GET.copy()
    params.pop('page', None)
    encoded = params.urlencode()
    return f'&{encoded}' if encoded else ''


@login_required(login_url='/admin/login/')
def dashboard(request):
    """Tableau de bord principal."""
    recent_factures = Facture.objects.select_related('client')[:6]
    context = {
        'total_factures': Facture.objects.count(),
        'total_clients': Client.objects.count(),
        'recent_factures': recent_factures,
    }
    return render(request, 'factures/dashboard.html', context)


@login_required(login_url='/admin/login/')
def user_settings(request):
    """Profil utilisateur et changement de mot de passe."""
    profile_form = UserSettingsForm(instance=request.user, prefix='profile')
    password_form = PasswordChangeForm(request.user, prefix='password')

    if request.method == 'POST':
        if request.POST.get('form_kind') == 'profile':
            profile_form = UserSettingsForm(request.POST, instance=request.user, prefix='profile')
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profil mis a jour.')
                return redirect('user_settings')
        elif request.POST.get('form_kind') == 'password':
            password_form = PasswordChangeForm(request.user, request.POST, prefix='password')
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Mot de passe mis a jour.')
                return redirect('user_settings')

    return render(request, 'factures/user_settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })


class ClientListView(LoginRequiredMixin, ListView):
    """Liste des clients avec recherche."""
    model = Client
    template_name = 'factures/clients_liste.html'
    context_object_name = 'clients'
    paginate_by = 50

    def get_queryset(self):
        qs = Client.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(nom__icontains=q) |
                Q(prenom__icontains=q) |
                Q(societe__icontains=q) |
                Q(email__icontains=q) |
                Q(telephone__icontains=q)
            )
        return qs.order_by('nom', 'prenom')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['page_query'] = pagination_context(self.request)
        return ctx


class FactureListView(LoginRequiredMixin, ListView):
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
        ctx['page_query'] = pagination_context(self.request)
        return ctx


@login_required(login_url='/admin/login/')
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, 'Client cree.')
            return redirect('clients_liste')
    else:
        form = ClientForm()

    return render(request, 'factures/client_form.html', {
        'form': form,
        'titre': 'Nouveau client',
    })


@login_required(login_url='/admin/login/')
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client mis a jour.')
            return redirect('clients_liste')
    else:
        form = ClientForm(instance=client)

    return render(request, 'factures/client_form.html', {
        'form': form,
        'client': client,
        'titre': 'Modifier client',
    })


@login_required(login_url='/admin/login/')
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        try:
            client.delete()
            messages.success(request, 'Client supprime.')
        except ProtectedError:
            messages.error(request, 'Ce client possede des factures et ne peut pas etre supprime.')
        return redirect('clients_liste')
    return render(request, 'factures/client_confirm_delete.html', {'client': client})


@login_required(login_url='/admin/login/')
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


@login_required(login_url='/admin/login/')
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


@login_required(login_url='/admin/login/')
def facture_detail(request, pk):
    """Détail d'une facture (aperçu HTML)."""
    facture = get_object_or_404(Facture, pk=pk)
    return render(request, 'factures/facture_detail.html', {
        'facture': facture,
    })


@login_required(login_url='/admin/login/')
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


@login_required(login_url='/admin/login/')
def facture_pdf(request, pk):
    """Génération PDF."""
    from .pdf_generator import generer_pdf_facture

    facture = get_object_or_404(Facture, pk=pk)
    pdf_bytes = generer_pdf_facture(facture)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f'Facture_{facture.numero_reservation}_{facture.client.nom}.pdf'
    # 'inline' = affiche dans le navigateur, 'attachment' = télécharge
    disposition = request.GET.get('disposition', 'inline')
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response
