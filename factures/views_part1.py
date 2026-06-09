"""Vues de l'application."""
import csv
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import ProtectedError, Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.utils import timezone

from .models import Facture, Client, ParametresHotel
from .forms import ClientForm, FactureForm, UserSettingsForm, PaymentForm


def pagination_context(request):
    params = request.GET.copy()
    params.pop('page', None)
    encoded = params.urlencode()
    return f'&{encoded}' if encoded else ''


@login_required(login_url='/admin/login/')
def dashboard(request):
    params = ParametresHotel.get_solo()
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    statut_filtre = request.GET.get('statut', '')
    paiement_filtre = request.GET.get('paiement', '')
    mois_filtre = request.GET.get('mois', '')
    annee_filtre = request.GET.get('annee', '')

    qs = Facture.objects.select_related('client')
    if date_debut:
        qs = qs.filter(date_arrivee__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_depart__lte=date_fin)
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)
    if paiement_filtre:
        qs = qs.filter(moyen_paiement=paiement_filtre)
    if mois_filtre:
        qs = qs.filter(date_arrivee__month=mois_filtre)
    if annee_filtre:
        qs = qs.filter(date_arrivee__year=annee_filtre)

    total_factures = qs.count()
    total_factures_payees = qs.filter(statut='ACQUITTE').count()
    total_factures_impayees = total_factures - total_factures_payees

    total_ht = Decimal('0.00')
    total_paye = Decimal('0.00')
    for f in qs:
        total_ht += f.montant_ht
        if f.statut == 'ACQUITTE':
            total_paye += f.total_ttc

    tva_rate = params.tva_defaut / Decimal('100')
    taxe_rate = params.taxe_sejour_pourcentage / Decimal('100')
    tva_total = (total_ht * tva_rate).quantize(Decimal('0.01'))
    taxe_sejour_total = (total_ht * taxe_rate).quantize(Decimal('0.01'))
    total_ttc = (total_ht + tva_total + taxe_sejour_total).quantize(Decimal('0.01'))
    total_impaye = (total_ttc - total_paye).quantize(Decimal('0.01'))

    revenus_par_mois = (
        Facture.objects
        .annotate(mois=TruncMonth('date_arrivee'))
        .values('mois')
        .annotate(
            total_ht_sum=Sum('prix_chambre_ht', field='prix_chambre_ht * CAST((julianday(date_depart) - julianday(date_arrivee)) AS INTEGER)', default=0),
            count=Count('id')
        )
        .order_by('-mois')[:12]
    )
    for r in revenus_par_mois:
        ht = r['total_ht_sum'] or Decimal('0.00')
        r['total'] = (ht * (Decimal('1') + tva_rate + taxe_rate)).quantize(Decimal('0.01'))

    paiements_stats = (
        qs.filter(moyen_paiement__gt='')
        .values('moyen_paiement')
        .annotate(
            total_ht_sum=Sum('prix_chambre_ht', field='prix_chambre_ht * CAST((julianday(date_depart) - julianday(date_arrivee)) AS INTEGER)', default=0),
            count=Count('id')
        )
        .order_by('-total_ht_sum')
    )
    for p in paiements_stats:
        ht = p['total_ht_sum'] or Decimal('0.00')
        p['total'] = (ht * (Decimal('1') + tva_rate + taxe_rate)).quantize(Decimal('0.01'))

    stats_mensuelles = []
    mois_stats = (
        Facture.objects
        .annotate(mois=TruncMonth('date_arrivee'))
        .values('mois')
        .annotate(
            arrivees=Count('id'),
            nuits_total=Sum('nombre_nuits', field='CAST((julianday(date_depart) - julianday(date_arrivee)) AS INTEGER)', default=0),
            personnes_total=Sum('nombre_personnes', default=0),
            revenu_ht=Sum('prix_chambre_ht', field='prix_chambre_ht * CAST((julianday(date_depart) - julianday(date_arrivee)) AS INTEGER)', default=0),
        )
        .order_by('-mois')[:12]
    )
    for m in mois_stats:
        ht = m['revenu_ht'] or Decimal('0.00')
        m['revenu_total'] = (ht * (Decimal('1') + tva_rate + taxe_rate)).quantize(Decimal('0.01'))

        mois_date = m['mois']
        clients_ids = (
            Facture.objects
            .filter(date_arrivee__year=mois_date.year, date_arrivee__month=mois_date.month)
            .values_list('client_id', flat=True)
            .distinct()
        )
        m['clients_uniques'] = len(clients_ids)

        clients_francais_ids = (
            Facture.objects
            .filter(
                date_arrivee__year=mois_date.year,
                date_arrivee__month=mois_date.month,
                client__pays='France'
            )
            .values_list('client_id', flat=True)
            .distinct()
        )
        m['clients_francais'] = len(clients_francais_ids)
        m['clients_etrangers'] = m['clients_uniques'] - m['clients_francais']

        if params.nombre_chambres > 0:
            jours_dans_mois = 30
            nuits_disponibles = params.nombre_chambres * jours_dans_mois
            nuits_occupees = int(m['nuits_total'] or 0)
            m['taux_occupation'] = round(nuits_occupees / nuits_disponibles * 100, 1) if nuits_disponibles > 0 else 0
            m['nuits_occupees'] = nuits_occupees
            m['nuits_disponibles'] = nuits_disponibles
        else:
            m['taux_occupation'] = 0

        stats_mensuelles.append(m)

    recent_factures = Facture.objects.select_related('client')[:6]

    context = {
        'params': params,
        'total_factures': total_factures,
        'total_clients': Client.objects.count(),
        'total_ht': total_ht,
        'tva_total': tva_total,
        'taxe_sejour_total': taxe_sejour_total,
        'total_ttc': total_ttc,
        'total_factures_payees': total_factures_payees,
        'total_factures_impayees': total_factures_impayees,
        'total_paye': total_paye,
        'total_impaye': total_impaye,
        'revenus_par_mois': revenus_par_mois,
        'paiements_stats': paiements_stats,
        'stats_mensuelles': stats_mensuelles,
        'recent_factures': recent_factures,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'statut_filtre': statut_filtre,
        'paiement_filtre': paiement_filtre,
        'mois_filtre': mois_filtre,
        'annee_filtre': annee_filtre,
    }
    return render(request, 'factures/dashboard.html', context)


@login_required(login_url='/admin/login/')
def user_settings(request):
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
