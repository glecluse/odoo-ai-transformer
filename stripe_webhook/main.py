# stripe_webhook/main.py

import stripe
import os
import functions_framework
from google.cloud import firestore
import secrets  # <-- Import pour générer une clé sécurisée

# Initialisation des clients
try:
    db = firestore.Client()
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
except Exception as e:
    print(f"Erreur d'initialisation : {e}")

@functions_framework.http
def stripe_webhook_handler(request):
    """Gère les webhooks Stripe, génère une clé de licence à l'activation."""
    if not webhook_secret:
        print("Erreur: Le secret du webhook n'est pas configuré.")
        return 'Configuration error', 500

    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        print(f"Erreur de vérification de la signature : {e}")
        return 'Invalid signature', 400

    # Gérer l'événement 'checkout.session.completed'
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        
        users_ref = db.collection('users')
        query = users_ref.where('stripe_customer_id', '==', customer_id).limit(1).stream()
        user_list = list(query)

        if user_list:
            user_id = user_list[0].id
            
            # 1. Générer une clé de licence unique et sécurisée
            license_key = f"lic_{secrets.token_hex(24)}"
            
            # 2. Mettre à jour la sous-collection 'subscriptions' avec la clé
            sub_ref = db.collection('users').document(user_id).collection('subscriptions').document(subscription_id)
            sub_data = {
                'status': 'active',
                'stripe_subscription_id': subscription_id,
                'stripe_customer_id': customer_id,
                'odoo_connection_name': session.get('metadata', {}).get('odoo_connection_name'),
                'price_id': session.get('line_items', {}).get('data', [{}])[0].get('price', {}).get('id'),
                'created_at': firestore.SERVER_TIMESTAMP,
                'license_key': license_key  # <-- On ajoute la clé ici
            }
            sub_ref.set(sub_data)
            
            print(f"Abonnement {subscription_id} activé pour l'utilisateur {user_id} avec la clé {license_key}.")

    # Gérer l'événement 'customer.subscription.deleted'
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        subscription_id = subscription.get('id')
        customer_id = subscription.get('customer')
        
        users_ref = db.collection('users')
        query = users_ref.where('stripe_customer_id', '==', customer_id).limit(1).stream()
        user_list = list(query)

        if user_list:
            user_id = user_list[0].id
            sub_ref = db.collection('users').document(user_id).collection('subscriptions').document(subscription_id)
            sub_ref.update({'status': 'canceled'})
            print(f"Abonnement {subscription_id} annulé pour l'utilisateur {user_id}.")

    return 'OK', 200