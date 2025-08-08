# auth.py (version finale et robuste)
import firebase_admin
from firebase_admin import credentials, auth
import json
import streamlit as st
import os

@st.cache_resource
def init_firebase():
    """
    Initialise Firebase Admin SDK.
    - En production (Cloud Run), utilise les Application Default Credentials.
    - En local, utilise le fichier de secrets.
    """
    # La présence de la variable K_SERVICE est l'indicateur le plus fiable de l'environnement Cloud Run.
    if "K_SERVICE" in os.environ: # <<< MODIFICATION DE LA CONDITION ICI
        try:
            # En production, le SDK trouve automatiquement les credentials
            creds = credentials.ApplicationDefault()
            if not firebase_admin._apps:
                firebase_admin.initialize_app(creds)
            return firebase_admin.get_app()
        except Exception as e:
            st.error(f"Erreur d'initialisation de Firebase en production : {e}")
            st.stop()
    
    # Si on n'est pas en production, on exécute la logique pour le local
    else:
        try:
            creds_json_str = st.secrets["firebase"]["service_account_key"]
            creds_dict = json.loads(creds_json_str)
            creds = credentials.Certificate(creds_dict)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(creds)
            return firebase_admin.get_app()
        except Exception as e:
            st.error(f"Erreur d'initialisation de Firebase en local depuis les secrets : {e}")
            st.stop()

def get_user_profile(id_token):
    """Vérifie un ID token et retourne le profil de l'utilisateur."""
    try:
        app = init_firebase()
        decoded_token = auth.verify_id_token(id_token, app=app)
        return decoded_token
    except Exception as e:
        print(f"Erreur de vérification du token : {e}")
        return None