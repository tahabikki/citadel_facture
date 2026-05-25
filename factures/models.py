"""
Modèles de la gestion des factures.
"""
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.urls import reverse


class ParametresHotel(models.Model):
    """Paramètres généraux de l'hôtel. Singleton (1 seule instance)."""
    nom = models.CharField(max_length=100, default='Hôtel Citadel')
    adresse = models.CharField(max_length=200, default='28 Rue Royale')
    code_postal = models.CharField(max_length=10, default='62100')
    ville = models.CharField(max_length=100, default='Calais')
    telephone = models.CharField(max_length=30, default='+33 668401405')
    email = models.EmailField(default='citadelhotel62@gmail.com')
    siret = models.CharField(max_length=20, default='837873785')
    capital = models.CharField(max_length=20, default='1000 €')

    tva_defaut = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('2.00'),
        help_text='Taux de TVA par défaut (%)'
    )
    taxe_sejour_defaut = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal('0.98'),
        help_text='Taxe de séjour par nuit/personne (€)'
    )
    prix_chambre_defaut = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('52.96'),
        help_text='Prix chambre HT par nuit (€)'
    )

    class Meta:
        verbose_name = 'Paramètres de l\'hôtel'
        verbose_name_plural = 'Paramètres de l\'hôtel'

    def __str__(self):
        return self.nom

    @classmethod
    def get_solo(cls):
        """Retourne l'instance unique, la crée si absente."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Client(models.Model):
    """Carnet d'adresses clients."""
    CIVILITE_CHOICES = [
        ('M.', 'Monsieur'),
        ('Mme', 'Madame'),
        ('Mlle', 'Mademoiselle'),
        ('Société', 'Société'),
    ]

    civilite = models.CharField(max_length=10, choices=CIVILITE_CHOICES, default='M.')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    societe = models.CharField(max_length=150, blank=True, verbose_name='Societe')
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    adresse = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'

    def __str__(self):
        identite = f'{self.civilite} {self.nom} {self.prenom}'.strip()
        return f'{identite} - {self.societe}' if self.societe else identite

    def nom_complet_majuscule(self):
        civ = dict(self.CIVILITE_CHOICES).get(self.civilite, self.civilite)
        identite = f'{civ} {self.nom.upper()} {self.prenom.upper()}'.strip()
        return f'{identite} - {self.societe.upper()}' if self.societe else identite


class Facture(models.Model):
    """Une facture de séjour."""
    STATUT_CHOICES = [
        ('PROVISOIRE', 'Document provisoire'),
        ('DEFINITIF', 'Facture définitive'),
        ('ACQUITTE', 'Facture acquittée'),
    ]

    numero_reservation = models.PositiveIntegerField(unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='factures')

    date_arrivee = models.DateField()
    date_depart = models.DateField()
    date_edition = models.DateField(auto_now_add=False)

    numero_chambre = models.PositiveIntegerField(default=1)
    nombre_personnes = models.PositiveIntegerField(default=1)
    type_sejour = models.CharField(max_length=100, default='Standard Normal')

    prix_chambre_ht = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text='Prix HT par nuit'
    )
    taxe_sejour_unitaire = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=Decimal('0.98'),
        help_text='Taxe séjour par nuit et par personne'
    )
    taux_tva = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('2.00'),
        help_text='Taux de TVA en %'
    )
    extras = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal('0.00')
    )

    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='PROVISOIRE'
    )
    notes = models.TextField(blank=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-cree_le']
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'

    def __str__(self):
        return f'Facture n°{self.numero_reservation} — {self.client}'

    def get_absolute_url(self):
        return reverse('facture_detail', kwargs={'pk': self.pk})

    # === CALCULS ===

    @property
    def nombre_nuits(self):
        return max(1, (self.date_depart - self.date_arrivee).days)

    @property
    def dates_nuitees(self):
        """Liste des dates de chaque nuit (= date d'arrivée jusqu'à veille du départ)."""
        nuits = []
        cur = self.date_arrivee
        while cur < self.date_depart:
            nuits.append(cur)
            cur += timedelta(days=1)
        return nuits

    @property
    def tva_par_nuit(self):
        return (self.prix_chambre_ht * self.taux_tva / Decimal('100')).quantize(Decimal('0.01'))

    @property
    def prix_chambre_ttc_par_nuit(self):
        return (self.prix_chambre_ht + self.tva_par_nuit).quantize(Decimal('0.01'))

    @property
    def taxe_sejour_par_nuit(self):
        """Taxe séjour par nuit = taxe unitaire × nb personnes."""
        return (self.taxe_sejour_unitaire * Decimal(self.nombre_personnes)).quantize(Decimal('0.01'))

    @property
    def total_chambre(self):
        return (self.prix_chambre_ttc_par_nuit * Decimal(self.nombre_nuits)).quantize(Decimal('0.01'))

    @property
    def total_taxe_sejour(self):
        return (self.taxe_sejour_par_nuit * Decimal(self.nombre_nuits)).quantize(Decimal('0.01'))

    @property
    def total_tva(self):
        return (self.tva_par_nuit * Decimal(self.nombre_nuits)).quantize(Decimal('0.01'))

    @property
    def total_ht(self):
        return (self.prix_chambre_ht * Decimal(self.nombre_nuits)).quantize(Decimal('0.01'))

    @property
    def total_hotel(self):
        return (self.total_chambre + self.total_taxe_sejour).quantize(Decimal('0.01'))

    @property
    def total_ttc(self):
        return (self.total_hotel + self.extras).quantize(Decimal('0.01'))

    @property
    def reste_du(self):
        if self.statut == 'ACQUITTE':
            return Decimal('0.00')
        return self.total_ttc

    @classmethod
    def prochain_numero(cls):
        """Suggère le prochain n° de réservation."""
        dernier = cls.objects.order_by('-numero_reservation').first()
        return (dernier.numero_reservation + 1) if dernier else 3300
