# firebase_auth_service.py
import requests
import streamlit as st
import json
import os

# --- Configuration ---
# Tente de lire la clé depuis les variables d'environnement (production)
# ou depuis le fichier secrets.toml (développement local)
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY") or st.secrets.get("firebase", {}).get("web_api_key")

# Vérification que la clé a bien été chargée
if not FIREBASE_WEB_API_KEY:
    # Cette erreur arrêtera l'application si la clé n'est pas trouvée, 
    # ce qui est plus sûr que de continuer avec une configuration invalide.
    raise ValueError("FIREBASE_WEB_API_KEY n'est pas configuré dans les secrets ou les variables d'environnement.")

# Les URLs des points d'API de Firebase
BASE_URL = "https://identitytoolkit.googleapis.com/v1/accounts"
SIGNUP_URL = f"{BASE_URL}:signUp?key={FIREBASE_WEB_API_KEY}"
SIGNIN_URL = f"{BASE_URL}:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
SEND_VERIFICATION_EMAIL_URL = f"{BASE_URL}:sendOobCode?key={FIREBASE_WEB_API_KEY}"
SIGNIN_WITH_IDP_URL = f"{BASE_URL}:signInWithIdp?key={FIREBASE_WEB_API_KEY}"


def register_user(email, password):
    """Crée un nouvel utilisateur via l'API REST de Firebase."""
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    try:
        response = requests.post(SIGNUP_URL, json=payload)
        response.raise_for_status()  # Lève une exception pour les erreurs HTTP (4xx ou 5xx)
        return response.json()  # Retourne les données de l'utilisateur (avec idToken)
    except requests.exceptions.HTTPError as err:
        error_json = err.response.json()
        error_message = error_json.get("error", {}).get("message", "Erreur inconnue.")
        return {"error": error_message}

def send_verification_email(id_token):
    """Demande à Firebase d'envoyer l'email de vérification à l'utilisateur."""
    payload = {
        "requestType": "VERIFY_EMAIL",
        "idToken": id_token
    }
    try:
        response = requests.post(SEND_VERIFICATION_EMAIL_URL, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        # Gérer les erreurs (ex: token expiré)
        return {"error": str(err)}

def login_user(email, password):
    """Connecte un utilisateur via l'API REST de Firebase."""
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    try:
        response = requests.post(SIGNIN_URL, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        error_json = err.response.json()
        error_message = error_json.get("error", {}).get("message", "Erreur inconnue.")
        # On traduit l'erreur la plus commune pour une meilleure expérience utilisateur
        if error_message == "INVALID_LOGIN_CREDENTIALS":
            return {"error": "Email ou mot de passe incorrect."}
        return {"error": error_message}

def login_with_google(id_token_from_google):
    """Connecte ou inscrit un utilisateur en utilisant un idToken de Google."""
    payload = {
        'postBody': f"id_token={id_token_from_google}&providerId=google.com",
        'requestUri': 'http://localhost:8501', # Cette URL doit correspondre à une URI autorisée dans votre client OAuth
        'returnIdpCredential': True,
        'returnSecureToken': True
    }
    try:
        response = requests.post(SIGNIN_WITH_IDP_URL, json=payload)
        response.raise_for_status()
        
        data = response.json()
        # On normalise la réponse pour qu'elle soit cohérente avec `login_user`
        return {
            "idToken": data.get("idToken"),
            "email": data.get("email"),
            "refreshToken": data.get("refreshToken"),
            "expiresIn": data.get("expiresIn"),
            "localId": data.get("localId"),
            "isNewUser": data.get("isNewUser", False)
        }
    except requests.exceptions.HTTPError as err:
        error_json = err.response.json()
        error_message = error_json.get("error", {}).get("message", "Erreur inconnue lors de l'authentification Google.")
        return {"error": error_message}