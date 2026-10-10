from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('virement/', views.virement_view, name='virement'), 
    path('infos_bancaires/', views.infos_bancaires_view, name='infos_bancaires'), 
    
    path('epargne/', views.epargne_view, name='epargne'),

    path('rib/pdf', views.download_rib_view, name="download_rib"),
    path('carte/toggle' , views.toggle_carte_view, name='toggle_carte'),
    path('recevoir/', views.recevoir_view, name='recevoir'),
    path('aide/', views.aide_view, name='aide'),
    path('support/', views.support, name='support'),
    path('particuliers/', views.particuliers_view, name='particuliers'),
    path('entreprises/', views.entreprises_view, name='entreprises'),
    path('mes-virements/', views.mes_virements_view, name='mes_virements'),

    path('virement/', views.virement_view, name='virement'),
    path('virement/verifier-code/', views.verifier_code_virement_view, name='verifier_code_virement'),
    path('virement/verifier-code/<int:id>/', views.verifier_code_virement_view, name='verifier_code_virement_id'),
    path('mes-virements/', views.mes_virements_view, name='mes_virements'),
    path('offres/', views.offres_view, name='offres'),


]