from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from .models import Compte
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate, login as auth_login
from django.shortcuts import get_object_or_404
from django.db import transaction as db_transaction
from .models import Compte, Transaction
from decimal import Decimal
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import qrcode
from io import BytesIO
from django.contrib import messages
from decimal import Decimal
import re
from .models import TicketSupport
from .models import Compte, Transaction, VirementExterne
from .models import MessageSupport

def home_view(request):
    return render(request, 'home.html')

def login_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Email ou mot de passe incorrect'})
    return render(request, 'login.html')

def register_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    
    if request.method == "POST":
        prenom = request.POST.get('prenom')
        nom = request.POST.get('nom')
        email = request.POST.get('email')
        telephone = request.POST.get('telephone')
        password = request.POST.get('password')

        # Vérifier si email existe déjà
        if User.objects.filter(username=email).exists():
            return render(request, 'register.html', {
                'error': 'Cet email est déjà utilisé'
            })

        # Créer User
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=prenom,
            last_name=nom
        )

        # Créer Compte bancaire lié
        Compte.objects.create(
            user=user,
            telephone=telephone,
            solde=50.00
        )

        # Connecter directement
        login(request, user)
        return redirect('dashboard')

    return render(request, 'register.html')



@login_required(login_url='/login/')
def dashboard_view(request):
    compte, created = Compte.objects.get_or_create(user=request.user)
    transactions = compte.transactions.all()[:10]
    return render(request, 'dashboard.html', {
        'compte': compte,
        'transactions': transactions
    })

def logout_view(request):
    auth_logout(request)
    return redirect('login')                                               


@login_required(login_url='/login/')



@login_required
def virement_view(request):
    compte = Compte.objects.get(user=request.user)
    
    if request.method == "POST":
        iban_dest = request.POST.get('iban','').strip()
        montant = Decimal(request.POST.get('montant', '0'))

        if compte.solde < montant:
            messages.error(request, "Solde insuffisant")
        else:
            # 1. On débite directement
            compte.solde -= montant
            compte.save()
            
            # 2. On crée le virement à 0%
            virement = VirementExterne.objects.create(
                user=request.user,
                iban_dest=iban_dest,
                nom_beneficiaire=request.POST.get('nom',''),
                montant=montant,
                progression=0,
                statut='attente_code1'
            )
            
            Transaction.objects.create(
                compte=compte, 
                label=f"Virement {virement.reference} vers {iban_dest}", 
                montant=-montant, 
                type='debit', 
                categorie='virement', 
                icon='↑'
            )
            
            request.session['virement_a_valider'] = virement.id
            return redirect('verifier_code_virement')

    return render(request, 'virement.html', {'compte': compte})

@login_required
def verifier_code_virement_view(request, id=None):
    v_id = request.session.get('virement_a_valider') or id
    if not v_id:
        return redirect('mes_virements')
        
    virement = get_object_or_404(VirementExterne, id=v_id, user=request.user)
    error = None

    if request.method == "POST":
        code_saisi = request.POST.get('code','').strip()
        
        # CODE 1 : 0% -> 50%
        if virement.progression == 0 and code_saisi == virement.code_50:
            virement.progression = 50
            virement.statut = 'attente_code2'
            virement.save()
        
        # CODE 2 : 50% -> 90%
        elif virement.progression == 50 and code_saisi == virement.code_90:
            virement.progression = 90
            virement.statut = 'attente_code3'
            virement.save()
        
        # CODE 3 : 90% -> 100% + CREDIT DESTINATAIRE
        elif virement.progression == 90 and code_saisi == virement.code_100:
            virement.progression = 100
            virement.statut = 'termine'
            virement.save()

            # CORRECTION ICI : numero_compt et pas iban
            try:
                dest = Compte.objects.get(numero_compt__iexact=virement.iban_dest)
                dest.solde += virement.montant
                dest.save()
                Transaction.objects.create(
                    compte=dest, 
                    label=f"Virement reçu {virement.reference}", 
                    montant=virement.montant, 
                    type='credit', 
                    categorie='virement', 
                    icon='↓'
                )
            except Compte.DoesNotExist:
                pass # IBAN externe, normal

            if 'virement_a_valider' in request.session:
                del request.session['virement_a_valider']
        else:
            error = "Code incorrect"

    return render(request, 'verifier_code.html', {'virement': virement, 'error': error})





@login_required(login_url='/login/')
def infos_bancaires_view(request):
    return render(request, 'infos_bancaires.html', {
        'compte': request.user.compte
    })


@login_required(login_url='/login/')
def toggle_carte_view(request):
    compte = request.user.compte
    compte.carte_bloquee = not compte.carte_bloquee
    compte.save()

    # Historique
    if compte.carte_bloquee:
        Transaction.objects.create(
            compte=compte,
            label="Blocage carte Visa",
            montant=0,
            type='debit',
            categorie='securite',
            icon='🔒'
        )
    else:
        Transaction.objects.create(
            compte=compte,
            label="Déblocage carte Visa",
            montant=0,
            type='credit',
            categorie='securite',
            icon='🔓'
        )

    return redirect('dashboard')



@login_required(login_url='/login/')
def epargne_view(request):
    compte = request.user.compte
    message = None
    error = None

    if request.method == "POST":
        action = request.POST.get('action') # depot ou retrait
        montant = request.POST.get('montant')

        try:
            montant = Decimal(montant)
            if montant <= 0:
                error = "Montant invalide"
            else:
                if action == "depot":
                    if montant > compte.solde:
                        error = f"Solde insuffisant, tu as {compte.solde}€"
                    else:
                        with db_transaction.atomic():
                            compte.solde -= montant
                            compte.epargne += montant
                            compte.save()
                            Transaction.objects.create(
                                compte=compte, 
                                label=f"Épargne - Dépôt", 
                                montant=montant, 
                                type='debit', 
                                categorie='epargne', 
                                icon='🐷'
                            )
                        message = f"{montant}€ ajoutés à ton épargne !"

                elif action == "retrait":
                    if montant > compte.epargne:
                        error = f"Épargne insuffisante, tu as {compte.epargne}€"
                    else:
                        with db_transaction.atomic():
                            compte.epargne -= montant
                            compte.solde += montant
                            compte.save()
                            Transaction.objects.create(
                                compte=compte, 
                                label=f"Épargne - Retrait", 
                                montant=montant, 
                                type='credit', 
                                categorie='epargne', 
                                icon='💰'
                            )
                        message = f"{montant}€ retirés vers ton compte courant !"

        except Exception as e:
            error = f"Erreur: {e}"

    return render(request, 'epargne.html', {
        'compte': compte,
        'message': message,
        'error': error
    })



@login_required(login_url='/login/')
def download_rib_view(request):
    compte = request.user.compte
    user = request.user

    # QR Code de l'IBAN
    qr = qrcode.QRCode(box_size=8, border=1)
    qr.add_data(compte.iban)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0033A0", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="RIB-{compte.numero_compte}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    w, h = A4

    # Bandeau
    p.setFillColorRGB(0, 0.2, 0.627) # #0033A0
    p.rect(0, h-110, w, 110, fill=1, stroke=0)
    p.setFillColorRGB(1,1,1)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(40, h-55, "BANQUE SUD")
    p.setFont("Helvetica", 11)
    p.drawString(40, h-75, "Relevé d'Identité Bancaire")

    # Infos
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, h-140, "Titulaire du compte :")
    p.setFont("Helvetica", 12)
    p.drawString(40, h-160, f"{user.first_name} {user.last_name}".upper())
    p.setFont("Helvetica", 10)
    p.drawString(40, h-175, user.email)

    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, h-210, "Domiciliation :")
    p.setFont("Helvetica", 10)
    p.drawString(40, h-225, "BANQUE SUD - TOULOUSE-FRANCE")
    p.drawString(40, h-238, "01 illes 1234 Toulouse, France")

    # Cadre RIB
    p.setStrokeColorRGB(0, 0.2, 0.627)
    p.setLineWidth(1.2)
    p.rect(40, h-370, w-80, 130, stroke=1, fill=0)

    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.5,0.5,0.5)
    p.drawString(55, h-270, "IBAN")
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(55, h-290, compte.iban)

    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.5,0.5,0.5)
    p.drawString(55, h-310, "BIC")
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(55, h-325, compte.bic)

    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.5,0.5,0.5)
    p.drawString(200, h-310, "N° COMPTE")
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(200, h-325, compte.numero_compte)

    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.5,0.5,0.5)
    p.drawString(55, h-345, "RIB")
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica", 10)
    p.drawString(55, h-360, compte.rib)

    # QR
    p.drawImage(ImageReader(qr_buffer), w-120, h-370, width=70, height=70)
    p.setFont("Helvetica", 6)
    p.setFillColorRGB(0.5,0.5,0.5)
    p.drawCentredString(w-85, h-378, "Scanner IBAN")

    p.setFont("Helvetica", 7)
    p.setFillColorRGB(0.6,0.6,0.6)
    p.drawString(40, 40, f"Document généré le {compte.created_at.strftime('%d/%m/%Y')} - BANQUE SUD")

    p.showPage()
    p.save()
    return response


@login_required(login_url='/login/')
def recevoir_view(request):
    compte = request.user.compte
    if request.method == 'POST':
        montant = Decimal(request.POST.get('montant', '0'))
        expediteur = request.POST.get('expediteur', 'Virement reçu')

        if montant <= 0:
            messages.error(request, "Montant invalide")
        else:
            compte.solde += montant
            compte.save()

            Transaction.objects.create(
                compte=compte,
                label=f"Reçu de {expediteur}",
                montant=montant,
                type='credit',
                categorie='virement',
                icon='↓'
            )
            messages.success(request, f"Tu as reçu {montant} € !")
            return redirect('dashboard')
            
    return render(request, 'recevoir.html', {'compte': compte})


def aide_view(request):
    return render(request, 'aide.html')


def particuliers_view(request):
    return render(request, 'particuliers.html')


def entreprises_view(request):
    return render(request, 'entreprises.html')




@login_required(login_url='/login/')
def mes_virements_view(request):
    virements = VirementExterne.objects.filter(user=request.user).order_by('-date_creation')
    compte = Compte.objects.get(user=request.user)
    return render(request, 'mes_virements.html', {
        'virements': virements,
        'compte': compte
    })


@login_required
def mes_virements_view(request):
    virements = VirementExterne.objects.filter(user=request.user).order_by('-date_creation')
    return render(request, 'mes_virements.html', {'virements': virements})



def offres_view(request):
    return render(request, 'offres.html')

def support(request):
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        sujet_text = request.POST.get('sujet', '').strip()  # on le récupère mais on le met dans le message

        if request.user.is_authenticated:
            nom = request.user.get_full_name() or request.user.username
            email = request.user.email
            user_obj = request.user
        else:
            nom = request.POST.get('nom', '').strip()
            email = request.POST.get('email', '').strip()
            user_obj = None

        if not message_text:
            messages.error(request, "Veuillez écrire un message.")
        else:
            # On combine sujet + message si sujet existe
            full_message = f"[{sujet_text}] {message_text}" if sujet_text else message_text

            MessageSupport.objects.create(
                utilisateur=user_obj,  # PAS user, bien utilisateur
                nom=nom,
                email=email,
                message=full_message
                # PAS de sujet, il n'existe pas dans ton modèle
            )
            messages.success(request, "Message envoyé avec succès !")
            return redirect('support')

    return render(request, 'support.html')