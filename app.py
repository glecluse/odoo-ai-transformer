# app.py (version corrigée avec la sauvegarde du firebase_uid)

import streamlit as st
from auth import get_user_profile 
import firebase_auth_service as auth_service
from streamlit_oauth import OAuth2Component
import os

# --- Configuration de la page ---
st.set_page_config(layout="wide", page_title="Odoo AI Transformer")

# --- Configuration et récupération des secrets ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or st.secrets.get("firebase", {}).get("google_client_id")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or st.secrets.get("firebase", {}).get("google_client_secret")

# --- Configuration pour le composant OAuth ---
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "openid email profile"
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501")

# --- Création du composant OAuth ---
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth_component = OAuth2Component(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        authorize_endpoint=AUTHORIZE_URL,
        token_endpoint=TOKEN_URL,
        refresh_token_endpoint=None,
        revoke_token_endpoint=None,
    )
else:
    oauth_component = None

# ==============================================================================
# --- LOGIQUE PRINCIPALE DE L'APPLICATION ---
# ==============================================================================

# CAS 1 : L'UTILISATEUR EST CONNECTÉ
if st.session_state.get('is_logged_in', False):
    st.sidebar.write(f"Connecté en tant que **{st.session_state['user_email']}**")
    if st.sidebar.button("Se déconnecter"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.title("✅ Bienvenue sur Odoo AI Transformer")
    
    if not st.session_state.get('email_verified', False):
        st.warning("⚠️ Votre adresse email n'a pas encore été vérifiée. Veuillez consulter l'email que nous vous avons envoyé pour finaliser votre inscription.")

    st.page_link("pages/4_Application.py", label="Accéder à l'application principale", icon="🚀")
    st.page_link("pages/3_Guide_Utilisation.py", label="Consulter le guide d'utilisation", icon="📖")

# CAS 2 : L'UTILISATEUR N'EST PAS CONNECTÉ
else:
    st.title("Accès à Odoo AI Transformer")
    
    login_tab, register_tab = st.tabs(["Se Connecter", "S'inscrire"])

    # --- Onglet de Connexion ---
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            login_button = st.form_submit_button("Se connecter")

            if login_button:
                response = auth_service.login_user(email, password)
                if "error" in response:
                    st.error(response["error"])
                else:
                    user_profile = get_user_profile(response.get('idToken'))
                    if not user_profile['email_verified']:
                        st.warning("Connexion réussie, mais votre adresse e-mail n'est pas encore vérifiée. Veuillez consulter vos emails.")

                    st.session_state['is_logged_in'] = True
                    st.session_state['user_email'] = user_profile.get('email')
                    st.session_state['email_verified'] = user_profile.get('email_verified', False)
                    # ▼▼▼ CORRECTION : LIGNE MANQUANTE AJOUTÉE ▼▼▼
                    st.session_state['firebase_uid'] = user_profile.get('uid')
                    st.rerun()
        
        st.markdown("<h3 style='text-align: center; color: grey;'>OU</h3>", unsafe_allow_html=True)
        
        # --- Bouton de connexion Google ---
        if not oauth_component:
            st.error("La configuration pour la connexion Google est manquante. Veuillez contacter le support.")
        else:
            result = oauth_component.authorize_button(
                name="Continuer avec Google",
                icon="https://www.google.com.tw/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png",
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                key="google_login",
                use_container_width=True
            )
            
            if result and "token" in result and "id_token" in result["token"]:
                id_token_google = result['token']['id_token']
                
                response = auth_service.login_with_google(id_token_google)
                if "error" in response:
                    st.error(response["error"])
                else:
                    user_profile = get_user_profile(response.get('idToken'))
                    st.session_state['is_logged_in'] = True
                    st.session_state['user_email'] = user_profile.get('email')
                    st.session_state['email_verified'] = True
                    # ▼▼▼ CORRECTION : LIGNE MANQUANTE AJOUTÉE ▼▼▼
                    st.session_state['firebase_uid'] = user_profile.get('uid')
                    st.rerun()

    # --- Onglet d'Inscription ---
    with register_tab:
        with st.form("register_form"):
            new_email = st.text_input("Email pour le nouveau compte")
            new_password = st.text_input("Mot de passe", type="password", key="new_password")
            confirm_password = st.text_input("Confirmez le mot de passe", type="password", key="confirm_password")
            register_button = st.form_submit_button("Créer le compte")

            if register_button:
                if new_password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(new_password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                else:
                    response = auth_service.register_user(new_email, new_password)
                    if "error" in response:
                        st.error(response["error"])
                    else:
                        id_token = response.get('idToken')
                        if id_token:
                            auth_service.send_verification_email(id_token)
                        st.success("Compte créé avec succès !")
                        st.info("Un email de vérification vous a été envoyé. Veuillez cliquer sur le lien dans l'email pour finaliser votre inscription, puis connectez-vous.")