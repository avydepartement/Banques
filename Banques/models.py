from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string

class Compte(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    numero_compte = models.CharField(max_length=20, unique=True) # ex: BN1234567890
    numero_carte = models.CharField(max_length=4, default="4242")
    solde = models.DecimalField(max_digits=12, decimal_places=2, default=50.00)
    epargne = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    carte_bloquee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.numero_compte}"

    @property
    def iban(self):
        # Génère un vrai IBAN affichable à partir de numero_compte
        num = self.numero_compte.replace("FR", "").replace(" ", "")
        num = (num + "000000000000")[:12] # complète si trop court
        return f"FR76 {num[:4]} {num[4:8]} {num[8:12]} {num[12:16] if len(num) > 12 else 'XXXX'}"

    @property
    def bic(self):
        return "BSUDXXXX"

    @property
    def rib(self):
        # RIB français : Banque Guichet Compte Clé
        compte_part = self.numero_compte[-10:].ljust(10, '0')
        return f"30003 12345 {compte_part} 42"

class Transaction(models.Model):
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='transactions')
    label = models.CharField(max_length=255)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=[('credit','credit'),('debit','debit')])
    categorie = models.CharField(max_length=50, default='virement')
    icon = models.CharField(max_length=10, default='💳')
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} - {self.montant}€"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('credit', 'Crédit'),
        ('debit', 'Débit'),
    ]

    CATEGORIE_CHOICES = [
        ('virement', 'Virement'),
        ('paiement', 'Paiement'),
        ('bonus', 'Bonus'),
        ('epargne', 'Épargne'),
        ('autre', 'Autre'),
    ]

    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='transactions')
    label = models.CharField(max_length=100)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES, default='autre')
    icon = models.CharField(max_length=10, default="💳")
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        signe = "+" if self.type == "credit" else "-"
        return f"{signe}{self.montant}€ - {self.label}"


    @property
    def iban(self):
        # Genere un IBAN a partir du numero_compte
        num = self.numero_compte.replace("FR", "")
        return f"FR76 {num[:4]} {num[:4:8]} {num[8:12]} {num[12:]}"

    @property
    def bic(self):
        return "BSUDXXX"

    @property
    def rib(self):
        return f"300003 12345 {self.numero_compte[-10:]} 42"



class TicketSupport(models.Model):
    SUJETS = [
        ('carte', 'Carte bancaire'),
        ('virement', 'Virement'),
        ('rib', 'RIB / IBAN'),
        ('epargne', 'Épargne'),
        ('autre', 'Autre'),
    ]
    STATUT = [
        ('nouveau', 'Nouveau'),
        ('en_cours', 'En cours'),
        ('resolu', 'Résolu'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sujet = models.CharField(max_length=20, choices=SUJETS)
    objet = models.CharField(max_length=200)
    message = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUT, default='nouveau')
    date_envoi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.objet} - {self.sujet} ({self.statut})"

    class Meta:
        verbose_name = "Ticket Support"
        ordering = ['-date_envoi']    



def generate_code():
    return ''.join(random.choices(string.digits, k=6))

def generate_ref():
    return 'VIR-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class VirementExterne(models.Model):
    STATUT_CHOICES = [
        ('attente_code1', 'En attente code 1'),
        ('attente_code2', 'En attente code 2'),
        ('attente_code3', 'En attente dernier code'),
        ('termine', 'Terminé'),
    ]

    reference = models.CharField(max_length=20, default=generate_ref, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='virements')
    
    # Destination
    iban_dest = models.CharField(max_length=34)
    nom_beneficiaire = models.CharField(max_length=100)
    montant = models.DecimalField(max_digits=10, decimal_places=2)

    # Progression 0% -> 50% -> 90% -> 100%
    progression = models.IntegerField(default=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='attente_code1')

    # Les 3 codes
    code_50 = models.CharField(max_length=6, default=generate_code)
    code_90 = models.CharField(max_length=6, default=generate_code)
    code_100 = models.CharField(max_length=6, default=generate_code)

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reference} - {self.progression}% - {self.montant}€"

    class Meta:
        ordering = ['-date_creation']



class MessageSupport(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nom = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    message = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message de {self.nom}"
