# stripe_service.py (version avec logs de débogage améliorés)

import stripe
import streamlit as st
import os
from database import get_firestore_client

# Configure la clé API Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY") or st.secrets.get("stripe", {}).get("secret_key")

# ... (la fonction get_or_create_customer reste identique) ...
def get_or_create_customer(email, firebase_uid):
    db = get_firestore_client()
    user_ref = db.collection('users').document(firebase_uid)
    user_doc = user_ref.get()
    
    if user_doc.exists and 'stripe_customer_id' in user_doc.to_dict():
        return user_doc.to_dict()['stripe_customer_id']
    else:
        customer = stripe.Customer.create(
            email=email,
            metadata={'firebase_uid': firebase_uid}
        )
        user_ref.set({'stripe_customer_id': customer.id, 'email': email}, merge=True)
        return customer.id

def create_checkout_session(customer_id, price_id, odoo_connection_name):
    """Crée une session de paiement Stripe Checkout."""
    prod_url = os.getenv("REDIRECT_URI", "http://localhost:8501")

    # --- LOGS DE DÉBOGAGE ---
    print(f"[DEBUG] Tentative de création de session Checkout.")
    print(f"[DEBUG] Customer ID: {customer_id}")
    print(f"[DEBUG] Price ID: {price_id}")
    print(f"[DEBUG] Clé API utilisée : {stripe.api_key[:11]}...") # Affiche les premiers caractères de la clé
    # --- FIN LOGS ---

    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f'{prod_url}/?payment=success',
            cancel_url=f'{prod_url}/?payment=cancel',
            metadata={'odoo_connection_name': odoo_connection_name}
        )
        print("[DEBUG] Session Checkout créée avec succès.")
        return checkout_session.url
    except Exception as e:
        print(f"[DEBUG] ERREUR BRUTE de l'API Stripe : {e}") # Affiche l'erreur complète dans les logs
        return str(e) # Renvoie l'erreur au frontend

# ... (la fonction create_customer_portal_session reste identique) ...
def create_customer_portal_session(customer_id):
    prod_url = os.getenv("REDIRECT_URI", "http://localhost:8501")
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=prod_url,
        )
        return portal_session.url
    except Exception as e:
        return str(e)