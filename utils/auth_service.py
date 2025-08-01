# Fichier : utils/auth_service.py
import streamlit as st
import requests
import json

API_KEY = st.secrets.get("WEB_API_KEY")

def sign_up(email, password):
    """Inscrit un nouvel utilisateur et demande l'envoi de l'e-mail de vérification."""
    signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(signup_url, data=json.dumps(payload))
    if response.status_code != 200:
        error_message = response.json().get('error', {}).get('message', 'Erreur inconnue.')
        raise Exception(f"Erreur d'inscription : {error_message}")
    id_token = response.json()['idToken']
    verify_email_url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    payload = {"requestType": "VERIFY_EMAIL", "idToken": id_token}
    requests.post(verify_email_url, data=json.dumps(payload))
    return True

def sign_in(email, password):
    """Connecte un utilisateur et retourne ses informations, y compris le jeton."""
    signin_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(signin_url, data=json.dumps(payload))
    if response.status_code != 200:
        error_message = response.json().get('error', {}).get('message', 'Email ou mot de passe incorrect.')
        raise Exception(f"Erreur de connexion : {error_message}")
    user_data = response.json()
    user_info = {
        "uid": user_data.get("localId"),
        "email": user_data.get("email"),
        "email_verified": user_data.get("emailVerified", False),
        "idToken": user_data.get("idToken")  # ### NOUVEAU ### : On garde le jeton
    }
    return user_info

def get_user_profile(id_token):
    """Récupère les informations à jour d'un utilisateur à partir de son jeton."""
    profile_url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={API_KEY}"
    payload = {"idToken": id_token}
    response = requests.post(profile_url, data=json.dumps(payload))
    if response.status_code != 200:
        # Le jeton a peut-être expiré, on force la déconnexion
        st.session_state.user_info = None
        st.rerun()
    
    # On retourne les informations du premier utilisateur trouvé
    user_data = response.json().get("users", [{}])[0]
    
    # On met à jour les informations en gardant le jeton
    updated_info = st.session_state.user_info.copy()
    updated_info["email_verified"] = user_data.get("emailVerified", False)
    
    return updated_info