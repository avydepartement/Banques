from django.contrib import admin
from .models import Compte, Transaction, VirementExterne, TicketSupport, MessageSupport

@admin.register(Compte)
class CompteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'numero_compte', 'numero_carte', 'solde', 'epargne', 'carte_bloquee', 'created_at')
    search_fields = ('numero_compte', 'numero_carte', 'user__username', 'user__email')
    list_filter = ('carte_bloquee',)
    readonly_fields = ('created_at', 'numero_compte')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'compte', 'label', 'montant', 'type', 'categorie', 'icon', 'date')
    list_filter = ('type', 'categorie')
    search_fields = ('label', 'compte__numero_compte', 'compte__user__username')
    readonly_fields = ('date',)

@admin.register(VirementExterne)
class VirementExterneAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'iban_dest', 'nom_beneficiaire', 'montant', 'progression', 'statut', 'date_creation')
    list_filter = ('statut', 'progression')
    search_fields = ('reference', 'iban_dest', 'nom_beneficiaire', 'user__username')
    readonly_fields = ('reference', 'code_50', 'code_90', 'code_100', 'date_creation')

    fieldsets = (
        ('Virement', {
            'fields': ('reference', 'user', 'iban_dest', 'nom_beneficiaire', 'montant')
        }),
        ('Progression', {
            'fields': ('progression', 'statut')
        }),
        ('Codes à envoyer au client', {
            'fields': ('code_50', 'code_90', 'code_100'),
            'description': '50% = code_50 | 90% = code_90 | 100% = code_100'
        }),
        ('Info', {
            'fields': ('date_creation',)
        }),
    )

@admin.register(TicketSupport)
class TicketSupportAdmin(admin.ModelAdmin):
    list_display = ('id', 'objet', 'user', 'sujet', 'statut', 'date_envoi')
    list_filter = ('statut', 'sujet')
    search_fields = ('objet', 'message', 'user__username')
    list_editable = ('statut',)
    readonly_fields = ('date_envoi',)

@admin.register(MessageSupport)
class MessageSupportAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'date_envoi', 'message_court')
    list_filter = ('date_envoi',)
    search_fields = ('nom', 'email', 'message')

    def message_court(self, obj):
        return obj.message[:50] + "..."
    message_court.short_description = "Message"