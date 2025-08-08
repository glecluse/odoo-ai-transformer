# database.py

import streamlit as st
from google.cloud import firestore
import os

@st.cache_resource
def get_firestore_client():
    """Initialise et retourne un client Firestore."""
    try:
        project_id = os.getenv("PROJECT_ID", "odoo-ai-transformer")
        db = firestore.Client(project=project_id)
        return db
    except Exception as e:
        st.error(f"Erreur de connexion à Firestore : {e}")
        return None

def save_connection(name, url, db_name, username, encrypted_password):
    """Sauvegarde ou met à jour une connexion Odoo pour l'utilisateur connecté dans Firestore."""
    try:
        user_id = st.session_state.get('firebase_uid')
        if not user_id:
            st.error("Utilisateur non identifié. Impossible de sauvegarder la connexion.")
            return

        db = get_firestore_client()
        if not db: return

        connections_ref = db.collection('users').document(user_id).collection('connections')
        query = connections_ref.where("name", "==", name).limit(1).stream()
        existing_docs = list(query)
        
        connection_data = {
            "name": name, "url": url, "db_name": db_name, "username": username,
            "encrypted_password": encrypted_password, "timestamp": firestore.SERVER_TIMESTAMP
        }

        if existing_docs:
            doc_id = existing_docs[0].id
            connections_ref.document(doc_id).set(connection_data, merge=True)
            print(f"Connexion '{name}' mise à jour pour l'utilisateur {user_id}.")
        else:
            connections_ref.add(connection_data)
            print(f"Nouvelle connexion '{name}' créée pour l'utilisateur {user_id}.")
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde dans Firestore : {e}")

def load_connections():
    """Charge toutes les connexions Odoo pour l'utilisateur connecté depuis Firestore."""
    try:
        user_id = st.session_state.get('firebase_uid')
        if not user_id: return [] 

        db = get_firestore_client()
        if not db: return []

        connections_ref = db.collection('users').document(user_id).collection('connections')
        query = connections_ref.order_by("name").stream()
        return [doc.to_dict() for doc in query]
    except Exception as e:
        st.error(f"Erreur lors du chargement depuis Firestore : {e}")
        return []

def init_db():
    """Fonction de compatibilité. Avec Firestore, aucune action n'est requise."""
    print("Initialisation de la base de données (Firestore) - Aucune action n'est requise.")
    pass

def get_active_subscriptions(user_id):
    """Récupère un dictionnaire des abonnements actifs pour un utilisateur."""
    if not user_id: return {}
    try:
        db = get_firestore_client()
        if not db: return {}
        subs_ref = db.collection('users').document(user_id).collection('subscriptions').stream()
        active_subscriptions = {}
        for sub in subs_ref:
            sub_data = sub.to_dict()
            if sub_data.get('status') in ('active', 'trialing'):
                active_subscriptions[sub_data.get('odoo_connection_name')] = sub_data
        return active_subscriptions
    except Exception as e:
        print(f"Erreur lors du chargement des abonnements : {e}")
        return {}

def is_connection_authorized(user_id, connection_name):
    """Vérifie si une connexion Odoo est autorisée (via abonnement ou plan gratuit)."""
    if not user_id or not connection_name: return False
    
    # Vérification 1 : L'utilisateur a-t-il un abonnement Stripe actif pour cette connexion ?
    active_subs = get_active_subscriptions(user_id)
    if connection_name in active_subs:
        print(f"Autorisation accordée pour '{connection_name}' via abonnement Stripe.")
        return True

    # Vérification 2 : La connexion a-t-elle une offre manuelle "free" ?
    try:
        db = get_firestore_client()
        if not db: return False
        
        conn_ref = db.collection('users').document(user_id).collection('connections')
        query = conn_ref.where("name", "==", connection_name).limit(1).stream()
        connection_doc = next(query, None) 

        if connection_doc and connection_doc.to_dict().get('plan_type') == 'free':
            print(f"Autorisation accordée pour '{connection_name}' via plan gratuit.")
            return True
    except Exception as e:
        print(f"Erreur lors de la vérification de l'autorisation : {e}")
        return False

    print(f"Autorisation refusée pour '{connection_name}'.")
    return False