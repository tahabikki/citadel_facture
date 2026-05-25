"""
Génération PDF d'une facture via ReportLab.
Reproduit fidèlement le format Hôtel Citadel.
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from .models import ParametresHotel


def _euro(value):
    """Format français 54,02 €."""
    return f'{value:.2f} €'.replace('.', ',')


def _date_fr(d):
    return d.strftime('%d/%m/%Y')


def generer_pdf_facture(facture):
    """Génère le PDF d'une facture et retourne les bytes."""
    params = ParametresHotel.get_solo()
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    # === EN-TÊTE ===
    y = page_h - 20 * mm

    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(page_w / 2, y, params.nom)
    y -= 7 * mm

    c.setFont('Helvetica', 11)
    c.drawCentredString(page_w / 2, y, params.adresse)
    y -= 5 * mm
    c.drawCentredString(page_w / 2, y, f'{params.code_postal}  {params.ville}')
    y -= 5 * mm
    c.drawCentredString(page_w / 2, y, f'Tél. : {params.telephone}')
    y -= 5 * mm
    c.drawCentredString(page_w / 2, y, params.email)
    y -= 12 * mm

    # === DATE D'ÉDITION (droite) ===
    c.setFont('Helvetica', 10)
    c.drawRightString(page_w - 20 * mm, y, f'Éditée le {_date_fr(facture.date_edition)}')
    y -= 12 * mm

    # === STATUT (gauche) + PAGE (droite) ===
    statut_label = dict(facture.STATUT_CHOICES).get(facture.statut, facture.statut).upper()
    c.setFont('Helvetica-Bold', 11)
    c.drawString(20 * mm, y, statut_label)
    c.setFont('Helvetica', 10)
    c.drawRightString(page_w - 20 * mm, y, 'Page   1/1')
    y -= 8 * mm

    # === RÉSERVATION + CLIENT ===
    c.setFont('Helvetica', 10)
    c.drawString(20 * mm, y, f'Réservation n° {facture.numero_reservation}')
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(page_w / 2, y, facture.client.nom_complet_majuscule())
    c.setFont('Helvetica', 10)
    y -= 6 * mm
    c.drawString(20 * mm, y, f'Arrivée : {_date_fr(facture.date_arrivee)}')
    y -= 5 * mm
    c.drawString(20 * mm, y, f'Départ : {_date_fr(facture.date_depart)}')
    y -= 10 * mm

    # === TABLEAU ===
    table_x = 20 * mm
    table_w = page_w - 40 * mm

    # Colonnes : Date | Chb | (vide) | Pers. | (vide) | Occupant | Taxe séjour | Chambre
    col_widths = [
        25 * mm,  # Date
        15 * mm,  # Chb
        15 * mm,  # vide
        15 * mm,  # Pers.
        20 * mm,  # vide
        25 * mm,  # Occupant
        25 * mm,  # Taxe séjour
        30 * mm,  # Chambre
    ]
    # Total largeur ~170mm = bon

    def x_col(i):
        return table_x + sum(col_widths[:i])

    row_h = 7 * mm

    # Ligne titre "Hôtel | Séjour : ..."
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(table_x, y - row_h, table_w, row_h, stroke=1, fill=0)
    c.setFont('Helvetica-BoldOblique', 10)
    c.drawString(table_x + 2 * mm, y - row_h + 2 * mm, 'Hôtel')
    c.setFont('Helvetica', 10)
    c.drawString(table_x + 25 * mm, y - row_h + 2 * mm, f'Séjour :   {facture.type_sejour}')
    y -= row_h

    # En-tête colonnes
    c.rect(table_x, y - row_h, table_w, row_h, stroke=1, fill=0)
    c.setFont('Helvetica-Bold', 9)
    headers = ['Date', 'Chb', '', 'Pers.', '', 'Occupant', 'Taxe séjour', 'Chambre']
    for i, h in enumerate(headers):
        # Lignes verticales
        if i > 0:
            c.line(x_col(i), y, x_col(i), y - row_h)
        if h:
            if i >= 6:  # alignement droite pour montants
                c.drawRightString(x_col(i) + col_widths[i] - 2 * mm, y - row_h + 2 * mm, h)
            else:
                c.drawString(x_col(i) + 2 * mm, y - row_h + 2 * mm, h)
    y -= row_h

    # Lignes de données (une par nuit)
    c.setFont('Helvetica', 9)
    taxe_par_nuit = facture.taxe_sejour_par_nuit
    prix_ttc_par_nuit = facture.prix_chambre_ttc_par_nuit

    for date_nuit in facture.dates_nuitees:
        c.rect(table_x, y - row_h, table_w, row_h, stroke=1, fill=0)
        for i in range(1, len(col_widths)):
            c.line(x_col(i), y, x_col(i), y - row_h)

        # Date
        c.drawString(x_col(0) + 2 * mm, y - row_h + 2 * mm, _date_fr(date_nuit))
        # Chambre
        c.drawString(x_col(1) + 2 * mm, y - row_h + 2 * mm, str(facture.numero_chambre))
        # Personnes
        c.drawString(x_col(3) + 2 * mm, y - row_h + 2 * mm, str(facture.nombre_personnes))
        # Taxe séjour
        c.drawRightString(x_col(6) + col_widths[6] - 2 * mm, y - row_h + 2 * mm, _euro(taxe_par_nuit))
        # Chambre TTC
        c.drawRightString(x_col(7) + col_widths[7] - 2 * mm, y - row_h + 2 * mm, _euro(prix_ttc_par_nuit))

        y -= row_h

    # === TOTAUX ===
    # On dessine des lignes sur les 2 dernières colonnes uniquement
    val_col_x = x_col(7)
    val_col_w = col_widths[7]
    taxe_col_x = x_col(6)
    taxe_col_w = col_widths[6]

    def ligne_total(label, val_chambre=None, val_taxe=None, bold=False):
        nonlocal y
        # Cadre pour les 2 colonnes de droite uniquement
        if val_taxe is not None:
            c.rect(taxe_col_x, y - row_h, taxe_col_w, row_h, stroke=1, fill=0)
        if val_chambre is not None:
            c.rect(val_col_x, y - row_h, val_col_w, row_h, stroke=1, fill=0)

        c.setFont('Helvetica-Bold' if bold else 'Helvetica', 9)
        # Label : à gauche de la colonne taxe
        c.drawRightString(taxe_col_x - 2 * mm, y - row_h + 2 * mm, label)
        if val_taxe is not None:
            c.drawRightString(taxe_col_x + taxe_col_w - 2 * mm, y - row_h + 2 * mm, _euro(val_taxe))
        if val_chambre is not None:
            c.drawRightString(val_col_x + val_col_w - 2 * mm, y - row_h + 2 * mm, _euro(val_chambre))
        y -= row_h

    ligne_total('Total', val_chambre=facture.total_chambre, val_taxe=facture.total_taxe_sejour, bold=True)
    ligne_total('Total Extra(s)', val_chambre=facture.extras)
    ligne_total('Total Hôtel', val_chambre=facture.total_hotel)

    y -= 2 * mm  # petit espace

    ligne_total('Total TTC', val_chambre=facture.total_ttc, bold=True)
    ligne_total(f'dont TVA {facture.taux_tva}%', val_chambre=facture.total_tva)
    ligne_total('Reste dû', val_chambre=facture.reste_du, bold=True)

    # === PIED DE PAGE ===
    c.setFont('Helvetica', 9)
    c.drawCentredString(
        page_w / 2, 15 * mm,
        f'{params.nom.upper()} {params.nom.lower()} Capital : {params.capital}'
    )
    c.drawCentredString(page_w / 2, 11 * mm, f'SIRET : {params.siret}')

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
