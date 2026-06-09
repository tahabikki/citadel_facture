# -*- coding: utf-8 -*-
"""Script to update views.py with extras formset handling."""
import os

# Read current views.py
views_path = os.path.join(os.path.dirname(__file__), 'factures', 'views.py')
with open(views_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the import line to include Extra and FactureExtraFormSet
old_import = "from .forms import ClientForm, FactureForm, UserSettingsForm, PaymentForm"
new_import = "from .forms import ClientForm, FactureForm, UserSettingsForm, PaymentForm, FactureExtraFormSet\nfrom .models import Extra, FactureExtra"
content = content.replace(old_import, new_import)

# Update facture_create to handle formset
old_create = """@login_required(login_url='/admin/login/')
def facture_create(request):
    \"\"\"Création d'une facture.\"\"\"
    params = ParametresHotel.get_solo()
    initial = {
        'numero_reservation': Facture.prochain_numero(),
        'date_edition': timezone.localdate(),
        'taux_tva': str(params.tva_defaut),
        'taux_taxe_sejour': str(params.taxe_sejour_pourcentage),
        'taxe_sejour_unitaire': str(params.taxe_sejour_defaut),
        'prix_chambre_ht': str(params.prix_chambre_defaut),
    }
    if request.method == 'POST':
        form = FactureForm(request.POST)
        if form.is_valid():
            facture = form.save()
            messages.success(request, 'Facture n\u00b0{} cr\u00e9\u00e9e.'.format(facture.numero_reservation))
            return redirect('facture_confirm_paiement', pk=facture.pk)
    else:
        form = FactureForm(initial=initial)

    return render(request, 'factures/facture_form.html', {
        'form': form,
        'titre': 'Nouvelle facture',
    })"""

new_create = """@login_required(login_url='/admin/login/')
def facture_create(request):
    \"\"\"Création d'une facture.\"\"\"
    params = ParametresHotel.get_solo()
    initial = {
        'numero_reservation': Facture.prochain_numero(),
        'date_edition': timezone.localdate(),
        'taux_tva': str(params.tva_defaut),
        'taux_taxe_sejour': str(params.taxe_sejour_pourcentage),
        'taxe_sejour_unitaire': str(params.taxe_sejour_defaut),
        'prix_chambre_ht': str(params.prix_chambre_defaut),
    }
    if request.method == 'POST':
        form = FactureForm(request.POST)
        formset = FactureExtraFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            facture = form.save()
            formset.instance = facture
            formset.save()
            messages.success(request, 'Facture n\u00b0{} cr\u00e9\u00e9e.'.format(facture.numero_reservation))
            return redirect('facture_confirm_paiement', pk=facture.pk)
    else:
        form = FactureForm(initial=initial)
        formset = FactureExtraFormSet()

    return render(request, 'factures/facture_form.html', {
        'form': form,
        'formset': formset,
        'titre': 'Nouvelle facture',
    })"""

content = content.replace(old_create, new_create)

# Update facture_update to handle formset
old_update = """@login_required(login_url='/admin/login/')
def facture_update(request, pk):
    \"\"\"Édition d'une facture.\"\"\"
    facture = get_object_or_404(Facture, pk=pk)
    if request.method == 'POST':
        form = FactureForm(request.POST, instance=facture)
        if form.is_valid():
            form.save()
            messages.success(request, 'Facture mise \u00e0 jour.')
            return redirect('facture_detail', pk=facture.pk)
    else:
        form = FactureForm(instance=facture)

    return render(request, 'factures/facture_form.html', {
        'form': form,
        'facture': facture,
        'titre': f'Modifier facture n\u00b0{facture.numero_reservation}',
    })"""

new_update = """@login_required(login_url='/admin/login/')
def facture_update(request, pk):
    \"\"\"Édition d'une facture.\"\"\"
    facture = get_object_or_404(Facture, pk=pk)
    if request.method == 'POST':
        form = FactureForm(request.POST, instance=facture)
        formset = FactureExtraFormSet(request.POST, instance=facture)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Facture mise \u00e0 jour.')
            return redirect('facture_detail', pk=facture.pk)
    else:
        form = FactureForm(instance=facture)
        formset = FactureExtraFormSet(instance=facture)

    return render(request, 'factures/facture_form.html', {
        'form': form,
        'formset': formset,
        'facture': facture,
        'titre': f'Modifier facture n\u00b0{facture.numero_reservation}',
    })"""

content = content.replace(old_update, new_update)

# Update facture_detail to include extras
old_detail = """@login_required(login_url='/admin/login/')
def facture_detail(request, pk):
    \"\"\"Détail d'une facture (aperçu HTML).\"\"\"
    facture = get_object_or_404(Facture, pk=pk)
    return render(request, 'factures/facture_detail.html', {
        'facture': facture,
    })"""

new_detail = """@login_required(login_url='/admin/login/')
def facture_detail(request, pk):
    \"\"\"Détail d'une facture (aperçu HTML).\"\"\"
    facture = get_object_or_404(Facture, pk=pk)
    extras = facture.facture_extras.all()
    return render(request, 'factures/facture_detail.html', {
        'facture': facture,
        'extras': extras,
    })"""

content = content.replace(old_detail, new_detail)

# Update dashboard to include extras stats
old_dashboard_import = """from .models import Facture, Client, ParametresHotel"""
new_dashboard_import = """from .models import Facture, Client, ParametresHotel, Extra, FactureExtra"""
# Already handled by the general import change above

# Update dashboard context to add extras stats
old_dashboard_context = """    context = {
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
        'statut_choices': Facture.STATUT_CHOICES,
        'paiement_choices': [c for c in Facture.PAIEMENT_CHOICES if c[0]],
    }"""

new_dashboard_context = """    total_extras_revenu = Decimal('0.00')
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
        'statut_choices': Facture.STATUT_CHOICES,
        'paiement_choices': [c for c in Facture.PAIEMENT_CHOICES if c[0]],
        'extras_stats': extras_stats,
        'total_extras_revenu': total_extras_revenu,
    }"""

content = content.replace(old_dashboard_context, new_dashboard_context)

# Update export_csv to include extras columns
old_csv_columns = """    columns = request.GET.getlist('cols')
    if not columns:
        columns = [
            'numero_reservation', 'client', 'date_arrivee', 'date_depart',
            'nombre_nuits', 'nombre_personnes', 'montant_ht', 'montant_tva',
            'montant_taxe_sejour', 'total_ttc', 'moyen_paiement',
            'date_paiement', 'statut'
        ]"""

new_csv_columns = """    columns = request.GET.getlist('cols')
    if not columns:
        columns = [
            'numero_reservation', 'client', 'date_arrivee', 'date_depart',
            'nombre_nuits', 'nombre_personnes', 'montant_ht', 'montant_tva',
            'montant_taxe_sejour', 'total_extras', 'total_ttc', 'moyen_paiement',
            'date_paiement', 'statut'
        ]"""

content = content.replace(old_csv_columns, new_csv_columns)

# Update CSV header map to include extras
old_header_map = """    header_map = {
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
        'date_paiement': 'Date paiement',
        'statut': 'Statut',
        'date_edition': 'Date \u00e9dition',
        'numero_chambre': 'Chambre',
        'type_sejour': 'Type s\u00e9jour',
        'extras': 'Extras',
        'notes': 'Notes',
    }"""

new_header_map = """    header_map = {
        'numero_reservation': 'N\u00b0 R\u00e9servation',
        'client': 'Client',
        'date_arrivee': 'Date arriv\u00e9e',
        'date_depart': 'Date d\u00e9part',
        'nombre_nuits': 'Nuits',
        'nombre_personnes': 'Personnes',
        'montant_ht': 'Montant HT',
        'montant_tva': 'TVA',
        'montant_taxe_sejour': 'Taxe s\u00e9jour',
        'total_extras': 'Total extras',
        'total_ttc': 'Total TTC',
        'moyen_paiement': 'Moyen paiement',
        'date_paiement': 'Date paiement',
        'statut': 'Statut',
        'date_edition': 'Date \u00e9dition',
        'numero_chambre': 'Chambre',
        'type_sejour': 'Type s\u00e9jour',
        'extras_detail': 'Extras d\u00e9tail',
        'notes': 'Notes',
    }"""

content = content.replace(old_header_map, new_header_map)

# Update CSV row generation to handle extras
old_csv_row = """            elif col in ('montant_ht', 'montant_tva', 'montant_taxe_sejour', 'total_ttc', 'extras'):
                val = getattr(f, col, Decimal('0.00'))
                row.append(f'{val:.2f}'.replace('.', ','))"""

new_csv_row = """            elif col in ('montant_ht', 'montant_tva', 'montant_taxe_sejour', 'total_ttc', 'extras', 'total_extras'):
                if col == 'total_extras':
                    val = f.total_extras_calcule
                else:
                    val = getattr(f, col, Decimal('0.00'))
                row.append(f'{val:.2f}'.replace('.', ','))
            elif col == 'extras_detail':
                extras_list = f.facture_extras.all()
                if extras_list:
                    details = '; '.join(f'{e.extra.nom} x{e.quantite} = {e.total_price} \u20ac' for e in extras_list)
                    row.append(details)
                else:
                    row.append('')"""

content = content.replace(old_csv_row, new_csv_row)

# Update export_pdf to include extras in totals
old_export_pdf_totals = """    for f in qs:
        total_ht += f.montant_ht
        total_tva += f.montant_tva
        total_taxe += f.montant_taxe_sejour
        total_extras += f.extras
        total_factures += 1
        mp = f.moyen_paiement or 'Non sp\u00e9cifi\u00e9'
        paiements[mp] = paiements.get(mp, 0) + 1

    total_ttc = total_ht + total_tva + total_taxe + total_extras"""

new_export_pdf_totals = """    for f in qs:
        total_ht += f.montant_ht
        total_tva += f.montant_tva
        total_taxe += f.montant_taxe_sejour
        total_extras += f.total_extras_calcule
        total_factures += 1
        mp = f.moyen_paiement or 'Non sp\u00e9cifi\u00e9'
        paiements[mp] = paiements.get(mp, 0) + 1

    total_ttc = total_ht + total_tva + total_taxe + total_extras"""

content = content.replace(old_export_pdf_totals, new_export_pdf_totals)

# Update export_pdf to include extras in detail rows
old_pdf_detail = """        data = [
            str(f.numero_reservation),
            str(f.client)[:20],
            f.date_arrivee.strftime('%d/%m/%Y'),
            f.date_depart.strftime('%d/%m/%Y'),
            _euro(f.montant_ht),
            _euro(f.montant_tva),
            _euro(f.montant_taxe_sejour),
            _euro(f.total_ttc),
        ]"""

new_pdf_detail = """        extras_total = f.total_extras_calcule
        data = [
            str(f.numero_reservation),
            str(f.client)[:20],
            f.date_arrivee.strftime('%d/%m/%Y'),
            f.date_depart.strftime('%d/%m/%Y'),
            _euro(f.montant_ht),
            _euro(f.montant_tva),
            _euro(f.montant_taxe_sejour),
            _euro(extras_total),
            _euro(f.total_ttc),
        ]"""

content = content.replace(old_pdf_detail, new_pdf_detail)

# Update PDF column headers
old_pdf_headers = """    c.setFont('Helvetica-Bold', 8)
    headers = ['N\u00b0', 'Client', 'Arriv\u00e9e', 'D\u00e9part', 'HT', 'TVA', 'Taxe', 'Total']
    col_widths = [15, 40, 20, 20, 22, 22, 22, 25]"""

new_pdf_headers = """    c.setFont('Helvetica-Bold', 8)
    headers = ['N\u00b0', 'Client', 'Arriv\u00e9e', 'D\u00e9part', 'HT', 'TVA', 'Taxe', 'Extras', 'Total']
    col_widths = [15, 35, 18, 18, 20, 20, 20, 20, 25]"""

content = content.replace(old_pdf_headers, new_pdf_headers)

# Update export_csv_page to include extras
old_csv_page_export = """    return render(request, 'factures/export_csv.html', {
        'clients': clients,
        'statut_choices': Facture.STATUT_CHOICES,
        'paiement_choices': [c for c in Facture.PAIEMENT_CHOICES if c[0]],
    })"""

new_csv_page_export = """    extras_list = Extra.objects.filter(actif=True).order_by('nom')
    return render(request, 'factures/export_csv.html', {
        'clients': clients,
        'statut_choices': Facture.STATUT_CHOICES,
        'paiement_choices': [c for c in Facture.PAIEMENT_CHOICES if c[0]],
        'extras_list': extras_list,
    })"""

content = content.replace(old_csv_page_export, new_csv_page_export)

with open(views_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Updated views.py: {len(content)} bytes')
