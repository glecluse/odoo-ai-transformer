# pages/5_Abonnement.py (Corrigé)

import streamlit as st
import os
import database as db
import stripe_service

# Gardien d'authentification
if not st.session_state.get('is_logged_in', False):
    st.error("🔒 Accès réservé aux utilisateurs connectés.")
    st.page_link("app.py", label="Retour à l'accueil", icon="🏠")
    st.stop()

st.title("Gérer mes Abonnements")

# Récupère l'ID de prix depuis les secrets
PRICE_ID = os.getenv("STRIPE_PRICE_ID") or st.secrets.get("stripe", {}).get("price_id")

if not PRICE_ID:
    st.error("La configuration des tarifs n'est pas complète. L'ID de prix est manquant.")
    st.stop()

# Charger les connexions Odoo de l'utilisateur
connections = db.load_connections()
user_id = st.session_state.get('firebase_uid')

if not connections:
    st.warning("Vous n'avez pas encore de connexion Odoo configurée.")
    st.page_link("pages/4_Application.py", label="Accéder à l'application et ajouter une connexion", icon="🚀")
else:
    st.info("Un abonnement de 29€ HT/mois est requis pour chaque connexion Odoo que vous souhaitez utiliser.")
    
    for conn in connections:
        conn_name = conn.get('name', 'Connexion sans nom')
        
        # ==============================================================================
        # ▼▼▼ CORRECTION CI-DESSOUS : On utilise la fonction d'autorisation complète ▼▼▼
        # ==============================================================================
        is_authorized = db.is_connection_authorized(user_id, conn_name)

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(conn_name)
                st.write(f"URL: {conn.get('url')} | DB: {conn.get('db_name')}")
            
            with col2:
                if is_authorized:
                    st.success("✅ Accès Actif") # Le texte est plus générique (Abonnement ou Offert)
                else:
                    if st.button(f"S'abonner pour {conn_name}", key=conn_name, type="primary"):
                        with st.spinner("Création de votre session de paiement..."):
                            customer_id = stripe_service.get_or_create_customer(
                                st.session_state['user_email'],
                                user_id
                            )
                            checkout_url = stripe_service.create_checkout_session(
                                customer_id, PRICE_ID, conn_name
                            )
                            # Logique de gestion de la réponse...
                            if checkout_url and checkout_url.startswith('https://checkout.stripe.com'):
                                st.markdown(f'<meta http-equiv="refresh" content="0; url={checkout_url}">', unsafe_allow_html=True)
                                st.link_button("Procéder au paiement", checkout_url)
                            else:
                                st.error("Impossible de créer la session de paiement. Erreur retournée par Stripe :")
                                st.error(checkout_url)

# --- Section de gestion de la facturation ---
st.markdown("---")
st.header("Gestion de la facturation")
st.write("Mettez à jour vos informations de paiement, consultez vos factures ou annulez un abonnement via notre portail sécurisé.")
if st.button("Accéder à mon portail de facturation"):
     with st.spinner("Chargement du portail client..."):
        customer_id = stripe_service.get_or_create_customer(
            st.session_state['user_email'],
            user_id
        )
        portal_url = stripe_service.create_customer_portal_session(customer_id)
        if portal_url and portal_url.startswith('https://billing.stripe.com'):
            st.markdown(f'<meta http-equiv="refresh" content="0; url={portal_url}">', unsafe_allow_html=True)
            st.link_button("Accéder à mon portail de facturation", portal_url)
        else:
            st.error("Impossible de créer la session du portail client. Erreur retournée par Stripe :")
            st.error(portal_url)