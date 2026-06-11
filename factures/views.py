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
from .forms import ClientForm, FactureForm, UserSettingsForm, FactureExtraFormSet
from .models import Extra, FactureExtra


def pagination_context(request):
    params = request.GET.copy()
    params.pop('page', None)
    encoded = params.urlencode()
    return f'&{encoded}' if encoded else ''


@login_required(login_url='/admin/login/')
def dashboard(request):
    """Tableau de bord principal avec statistiques financières."""
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

    paiements_stats = (
        qs.filter(moyen_paiement__gt='')
        .values('moyen_paiement')
        .annotate(
            total_ht_sum=Sum(
                'prix_chambre_ht',
                field="prix_chambre_ht * CAST((julianday(date_depart) - julianday(date_arrivee)) AS INTEGER)",
                default=0
            ),
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
            nuits_total=Sum(
                'id',
                field="CAST((julianday(date_depart) - julianday(date_arrivee)) AS INTEGER)",
                default=0
            ),
            personnes_total=Sum('nombre_personnes', default=0),
            revenu_ht=Sum(
                'prix_chambre_ht',
                field="prix_chambre_ht * CAST((julianday(date_depart) - julianday(date_arrivee)) AS INTEGER)",
                default=0
            ),
        )
        .order_by('-mois')[:12]
    )
    for m in mois_stats:
        ht = m['revenu_ht'] or Decimal('0.00')
        m['revenu_total'] = (ht * (Decimal('1') + tva_rate + taxe_rate)).quantize(Decimal('0.01'))

        mois_date = m['mois']
        clients_ids = list(
            Facture.objects
            .filter(date_arrivee__year=mois_date.year, date_arrivee__month=mois_date.month)
            .values_list('client_id', flat=True)
            .distinct()
        )
        m['clients_uniques'] = len(clients_ids)

        clients_francais_ids = list(
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

    total_extras_revenu = Decimal('0.00')
    extras_stats = Extra.objects.annotate(
        total_quantite=Sum('factureextra__quantite', filter=Q(factureextra__facture__in=qs)),
        total_revenu=Sum('factureextra__total_price', filter=Q(factureextra__facture__in=qs)),
    ).order_by('-total_revenu')
    for e in extras_stats:
        if e.total_revenu:
            total_extras_revenu += e.total_revenu

    context = {
        'params': params,
        'total_factures': total_factures,
        'total_clients': Client.objects.count(),
        'total_ht': total_ht,
        'tva_total': tva_total,
        'taxe_sejour_total': taxe_sejour_total,
        'total_ttc': total_ttc,
        'total_factures_payees': total_factures_payees,
        'total_paye': total_paye,
        'paiements_stats': paiements_stats,
        'stats_mensuelles': stats_mensuelles,
        'recent_factures': recent_factures,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'statut_filtre': statut_filtre,
        'paiement_filtre': paiement_filtre,
        'mois_filtre': mois_filtre,
        'annee_filtre': annee_filtre,
        'statut_choices': Facture.STATUT_CHOICES,
        'paiement_choices': [c for c in Facture.PAIEMENT_CHOICES if c[0]],
        'extras_stats': extras_stats,
        'total_extras_revenu': total_extras_revenu,
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
    params = ParametresHotel.get_solo()
    initial = {
        'date_edition': timezone.localdate(),
        'taux_tva': str(params.tva_defaut),
        'taux_taxe_sejour': str(params.taxe_sejour_pourcentage),
        'taxe_sejour_unitaire': str(params.taxe_sejour_defaut),
        'prix_chambre_ht': str(params.prix_chambre_defaut),
    }
    paiement_choices = [c for c in Facture.PAIEMENT_CHOICES if c[0]]
    if request.method == 'POST':
        form = FactureForm(request.POST)
        formset = FactureExtraFormSet(request.POST)
        if form.is_valid():
            facture = form.save()
            mp = request.POST.get('moyen_paiement', '')
            if mp:
                facture.moyen_paiement = mp
                facture.statut = 'ACQUITTE'
                facture.save(update_fields=['moyen_paiement', 'statut'])
            formset = FactureExtraFormSet(request.POST, instance=facture)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Facture n\u00b0{} cr\u00e9\u00e9e.'.format(facture.numero_reservation))
                return redirect('facture_liste')
    else:
        form = FactureForm(initial=initial)
        formset = FactureExtraFormSet(instance=Facture())

    extras_list = Extra.objects.filter(actif=True).order_by('nom')
    return render(request, 'factures/facture_form.html', {
        'form': form,
        'formset': formset,
        'titre': 'Nouvelle facture',
        'paiement_choices': paiement_choices,
        'extras_list': extras_list,
    })


@login_required(login_url='/admin/login/')
def facture_update(request, pk):
    """Édition d'une facture."""
    facture = get_object_or_404(Facture, pk=pk)
    paiement_choices = [c for c in Facture.PAIEMENT_CHOICES if c[0]]
    if request.method == 'POST':
        form = FactureForm(request.POST, instance=facture)
        formset = FactureExtraFormSet(request.POST, instance=facture)
        if form.is_valid() and formset.is_valid():
            facture = form.save()
            mp = request.POST.get('moyen_paiement', '')
            if mp:
                facture.moyen_paiement = mp
                facture.statut = 'ACQUITTE'
            else:
                facture.moyen_paiement = ''
            facture.save(update_fields=['moyen_paiement', 'statut'])
            formset.save()
            messages.success(request, 'Facture mise \u00e0 jour.')
            return redirect('facture_detail', pk=facture.pk)
    else:
        form = FactureForm(instance=facture)
        formset = FactureExtraFormSet(instance=facture)

    extras_list = Extra.objects.filter(actif=True).order_by('nom')
    return render(request, 'factures/facture_form.html', {
        'form': form,
        'formset': formset,
        'facture': facture,
        'titre': f'Modifier facture n\u00b0{facture.numero_reservation}',
        'paiement_choices': paiement_choices,
        'extras_list': extras_list,
    })


@login_required(login_url='/admin/login/')
def facture_detail(request, pk):
    """Détail d'une facture (aperçu HTML)."""
    facture = get_object_or_404(Facture, pk=pk)
    extras = facture.facture_extras.all()
    return render(request, 'factures/facture_detail.html', {
        'facture': facture,
        'extras': extras,
    })


@login_required(login_url='/admin/login/')
def facture_delete(request, pk):
    """Suppression."""
    facture = get_object_or_404(Facture, pk=pk)
    if request.method == 'POST':
        num = facture.numero_reservation
        facture.delete()
        messages.success(request, f'Facture n\u00b0{num} supprim\u00e9e.')
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
    disposition = request.GET.get('disposition', 'inline')
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


@login_required(login_url='/admin/login/')
def export_csv(request):
    """Export CSV des factures avec choix des colonnes."""
    columns = request.GET.getlist('cols')
    if not columns:
        columns = [
            'numero_reservation', 'client', 'date_arrivee', 'date_depart',
            'nombre_nuits', 'nombre_personnes', 'montant_ht', 'montant_tva',
            'montant_taxe_sejour', 'total_extras', 'total_ttc', 'moyen_paiement',
            'statut'
        ]

    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    statut_filtre = request.GET.get('statut', '')
    paiement_filtre = request.GET.get('paiement', '')
    client_filtre = request.GET.get('client', '')

    qs = Facture.objects.select_related('client')
    if date_debut:
        qs = qs.filter(date_arrivee__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_depart__lte=date_fin)
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)
    if paiement_filtre:
        qs = qs.filter(moyen_paiement=paiement_filtre)
    if client_filtre:
        qs = qs.filter(client_id=client_filtre)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="factures_export.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)

    header_map = {
        'numero_reservation': 'N\u00b0 R\u00e9servation',
        'client': 'Client',
        'date_arrivee': 'Date arriv\u00e9e',
        'date_depart': 'Date d\u00e9part',
        'nombre_nuits': 'Nuits',
        'nombre_personnes': 'Personnes',
        'montant_ht': 'Montant HT',
        'montant_tva': 'TVA',
        'montant_taxe_sejour': 'Taxe s\u00e9jour',
        'total_ttc': 'Total TTC',
        'moyen_paiement': 'Moyen paiement',
        'statut': 'Statut',
        'date_edition': 'Date \u00e9dition',
        'numero_chambre': 'Chambre',
        'type_sejour': 'Type s\u00e9jour',
        'extras': 'Extras',
        'notes': 'Notes',
    }
    writer.writerow([header_map.get(c, c) for c in columns])

    for f in qs:
        row = []
        for col in columns:
            if col == 'client':
                row.append(str(f.client))
            elif col == 'statut':
                row.append(f.get_statut_display())
            elif col == 'moyen_paiement':
                row.append(f.get_moyen_paiement_display() if f.moyen_paiement else '')
            elif col in ('date_arrivee', 'date_depart', 'date_edition'):
                row.append(getattr(f, col).strftime('%d/%m/%Y'))
            elif col in ('montant_ht', 'montant_tva', 'montant_taxe_sejour', 'total_ttc', 'extras', 'total_extras'):
                if col == 'total_extras':
                    val = f.total_extras_calcule
                else:
                    val = getattr(f, col, Decimal('0.00'))
                row.append(f'{val:.2f}'.replace('.', ','))
            elif col == 'extras_detail':
                extras_list = f.facture_extras.all()
                if extras_list:
                    details = '; '.join(f'{e.extra.nom} x{e.quantite} = {e.total_price} €' for e in extras_list)
                    row.append(details)
                else:
                    row.append('')
            elif col == 'nombre_nuits':
                row.append(str(f.nombre_nuits))
            else:
                row.append(str(getattr(f, col, '')))
        writer.writerow(row)

    return response


@login_required(login_url='/admin/login/')
def bilan(request):
    """Page Bilan général avec tableau filtré et boutons d'export."""
    params = ParametresHotel.get_solo()

    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    statut_filtre = request.GET.get('statut', '')
    paiement_filtre = request.GET.get('paiement', '')
    client_filtre = request.GET.get('client', '')

    qs = Facture.objects.select_related('client').order_by('-date_arrivee')
    if date_debut:
        qs = qs.filter(date_arrivee__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_depart__lte=date_fin)
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)
    if paiement_filtre:
        qs = qs.filter(moyen_paiement=paiement_filtre)
    if client_filtre:
        qs = qs.filter(client_id=client_filtre)

    total_ht = Decimal('0.00')
    total_tva = Decimal('0.00')
    total_taxe = Decimal('0.00')
    total_extras = Decimal('0.00')
    total_ttc = Decimal('0.00')
    for f in qs:
        total_ht += f.montant_ht
        total_tva += f.montant_tva
        total_taxe += f.montant_taxe_sejour
        total_extras += f.total_extras_calcule
        total_ttc += f.total_ttc

    clients = Client.objects.all().order_by('nom', 'prenom')

    return render(request, 'factures/bilan.html', {
        'params': params,
        'factures': qs,
        'total_ht': total_ht,
        'total_tva': total_tva,
        'total_taxe': total_taxe,
        'total_extras': total_extras,
        'total_ttc': total_ttc,
        'total_factures': qs.count(),
        'date_debut': date_debut,
        'date_fin': date_fin,
        'statut_filtre': statut_filtre,
        'paiement_filtre': paiement_filtre,
        'client_filtre': client_filtre,
        'clients': clients,
        'statut_choices': Facture.STATUT_CHOICES,
        'paiement_choices': [c for c in Facture.PAIEMENT_CHOICES if c[0]],
    })


@login_required(login_url='/admin/login/')
def export_pdf(request):
    """Export PDF d'un état financier."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas

    params = ParametresHotel.get_solo()

    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    statut_filtre = request.GET.get('statut', '')
    paiement_filtre = request.GET.get('paiement', '')

    qs = Facture.objects.select_related('client')
    if date_debut:
        qs = qs.filter(date_arrivee__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_depart__lte=date_fin)
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)
    if paiement_filtre:
        qs = qs.filter(moyen_paiement=paiement_filtre)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    y = page_h - 20 * mm

    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(page_w / 2, y, params.nom)
    y -= 8 * mm
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(page_w / 2, y, '\u00c9tat financier')
    y -= 8 * mm
    c.setFont('Helvetica', 10)
    today_str = "Aujourd'hui"
    debut_str = "Début"
    dash = "\u2014"
    periode = f'Période: {date_debut or debut_str} {dash} {date_fin or today_str}'
    c.drawCentredString(page_w / 2, y, periode)
    y -= 8 * mm
    edited_str = "Édité le"
    c.drawCentredString(page_w / 2, y, f'{edited_str} {timezone.localdate().strftime("%d/%m/%Y")}')
    y -= 15 * mm

    total_ht = Decimal('0.00')
    total_tva = Decimal('0.00')
    total_taxe = Decimal('0.00')
    total_extras = Decimal('0.00')
    total_factures = 0
    paiements = {}

    for f in qs:
        total_ht += f.montant_ht
        total_tva += f.montant_tva
        total_taxe += f.montant_taxe_sejour
        total_extras += f.total_extras_calcule
        total_factures += 1
        mp = f.moyen_paiement or 'Non sp\u00e9cifi\u00e9'
        paiements[mp] = paiements.get(mp, 0) + 1

    total_ttc = total_ht + total_tva + total_taxe

    def _euro(val):
        return f'{val:.2f} \u20ac'.replace('.', ',')

    c.setStrokeColor(colors.HexColor('#5e4828'))
    c.setLineWidth(1.5)
    c.rect(20 * mm, y - 4 * mm, page_w - 40 * mm, 8 * mm, stroke=1, fill=0)
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(page_w / 2, y + 1 * mm, f'CHIFFRE D\'AFFAIRES (HT)')
    c.drawRightString(page_w - 25 * mm, y + 1 * mm, _euro(total_ht))
    y -= 16 * mm

    c.setFont('Helvetica-Bold', 12)
    c.drawString(20 * mm, y, f'R\u00e9sum\u00e9 - {total_factures} facture(s)')
    y -= 10 * mm

    c.setFont('Helvetica', 10)
    items = [
        ('Chiffre d\'affaires (HT)', _euro(total_ht)),
        ('TVA ({0}%)'.format(params.tva_defaut), _euro(total_tva)),
        ('Taxe s\u00e9jour ({0}%)'.format(params.taxe_sejour_pourcentage), _euro(total_taxe)),
    ]
    for label, val in items:
        c.drawString(25 * mm, y, label)
        c.drawRightString(page_w - 25 * mm, y, val)
        y -= 7 * mm

    c.setFont('Helvetica-Bold', 12)
    c.setStrokeColor(colors.HexColor('#5e4828'))
    c.line(25 * mm, y, page_w - 25 * mm, y)
    y -= 3 * mm
    c.drawString(25 * mm, y, 'Total TTC')
    c.drawRightString(page_w - 25 * mm, y, _euro(total_ttc))

    y -= 10 * mm
    c.setFont('Helvetica-Bold', 12)
    c.drawString(20 * mm, y, 'R\u00e9partition par moyen de paiement')
    y -= 8 * mm
    c.setFont('Helvetica', 10)
    for mp, count in paiements.items():
        c.drawString(25 * mm, y, f'{mp}: {count} facture(s)')
        y -= 6 * mm

    y -= 15 * mm
    c.setFont('Helvetica-Bold', 12)
    c.drawString(20 * mm, y, 'D\u00e9tail des factures')
    y -= 8 * mm

    # En-tête de tableau
    c.setFont('Helvetica-Bold', 8)
    headers = ['N\u00b0', 'Client', 'Arriv\u00e9e', 'D\u00e9part', 'HT', 'Extras', 'TVA', 'Taxe', 'Total']
    col_widths = [14, 38, 17, 17, 18, 16, 16, 16, 18]
    x_start = 20 * mm
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        c.drawString(x_start + sum(col_widths[:i]) * mm, y, h)
    y -= 6 * mm

    c.setFont('Helvetica', 7)
    for f in qs:
        if y < 30 * mm:
            c.showPage()
            y = page_h - 20 * mm
            c.setFont('Helvetica', 7)
        data = [
            str(f.numero_reservation),
            str(f.client)[:16],
            f.date_arrivee.strftime('%d/%m/%Y'),
            f.date_depart.strftime('%d/%m/%Y'),
            _euro(f.montant_ht),
            _euro(f.total_extras_calcule),
            _euro(f.montant_tva),
            _euro(f.montant_taxe_sejour),
            _euro(f.total_ttc),
        ]
        for i, (d, w) in enumerate(zip(data, col_widths)):
            c.drawString(x_start + sum(col_widths[:i]) * mm, y, d)
        y -= 5 * mm

    # Pied de page
    c.setFont('Helvetica', 8)
    c.drawCentredString(page_w / 2, 15 * mm, f'{params.nom.upper()} | SIRET: {params.siret}')

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="etat_financier.pdf"'
    return response
