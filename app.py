import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import os
import openai
import stripe
import time
import json
from utils.db import (
    get_or_create_user,
    update_user_subscription,
    load_connections,
    save_connection
)
from utils.security import SAVED_PASSWORD_PLACEHOLDER


# === INIT FONCTION POUR INITIALISATION FIREBASE SANS RECURSION ===
def initialize_firebase():
    if not firebase_admin._apps:
        firebase_cred_dict = dict(st.secrets["firebase_service_account"])

        # Corriger la clé privée en remplaçant '\\n' par retours à la ligne réels
        if "private_key" in firebase_cred_dict:
            firebase_cred_dict["private_key"] = firebase_cred_dict["private_key"].replace('\\n', '\n')

        cred = credentials.Certificate(firebase_cred_dict)
        firebase_admin.initialize_app(cred)


initialize_firebase()


@st.cache_data(show_spinner=False)
def verify_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        st.error(f"Erreur d'authentification : {e}")
        return None


# === INTERFACE LOGIN ===
def login_ui():
    st.title("🔐 Connexion")
    email = st.text_input("Adresse email")
    password = st.text_input("Mot de passe", type="password")
    login = st.button("Se connecter")

    if login:
        import requests
        api_key = st.secrets["WEB_API_KEY"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            id_token = response.json().get("idToken")
            st.session_state.id_token = id_token
            # On évite st.rerun ici pour limiter risques de récursion
        except Exception:
            st.error("Identifiants invalides")


# === AUTHENTIFICATION ET GESTION DE SESSION ===
if "id_token" not in st.session_state:
    login_ui()
    st.stop()

user_info = verify_token(st.session_state["id_token"])
if not user_info:
    st.error("Impossible de vérifier le token utilisateur.")
    st.stop()

user_id = user_info.get("uid")
email = user_info.get("email")
st.session_state.user_id = user_id
st.session_state.email = email


# === ABONNEMENT STRIPE ===
stripe.api_key = st.secrets["stripe"]["secret_key"]
price_id = st.secrets["stripe"]["price_id"]

user_db_data = get_or_create_user(user_id, email)
if not user_db_data:
    st.error("❌ Impossible de récupérer les infos utilisateur depuis la base.")
    st.stop()

if not user_db_data or user_db_data.get("subscription_status") != "active":
    st.warning("⛔️ Abonnement inactif. Veuillez vous abonner pour continuer.")
    st.markdown("## 🔄 Abonnement")
    if st.button("S'abonner via Stripe"):
        import requests
        url = "https://api.stripe.com/v1/checkout/sessions"
        headers = {
            "Authorization": f"Bearer {stripe.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "success_url": st.request.url,
            "cancel_url": st.request.url,
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "customer_email": email
        }
        res = requests.post(url, headers=headers, data=data)
        if res.status_code == 200:
            checkout_url = res.json().get("url")
            st.markdown(f"[👉 Accéder au paiement Stripe]({checkout_url})")
        else:
            st.error("Erreur lors de la création de la session de paiement.")
    st.stop()


# === INTERFACE PRINCIPALE ===
st.title("🧠 Odoo AI Transformer")

st.markdown("## 🔗 Connexions à vos bases Odoo")

connections = load_connections(user_id)
for conn in connections:
    with st.expander(conn["name"]):
        st.write(f"- URL : {conn['url']}")
        st.write(f"- Base de données : {conn['db_name']}")
        st.write(f"- Utilisateur : {conn['username']}")

st.markdown("## ➕ Ajouter une nouvelle connexion")

with st.form("new_connection_form"):
    name = st.text_input("Nom de la connexion")
    url = st.text_input("URL de l'instance Odoo (ex: https://demo.odoo.com)")
    db_name = st.text_input("Nom de la base de données")
    username = st.text_input("Nom d'utilisateur Odoo")
    password = st.text_input("Mot de passe", type="password")
    submit = st.form_submit_button("Enregistrer")

    if submit:
        save_connection(
            user_id=user_id,
            name=name,
            url=url,
            db_name=db_name,
            username=username,
            password=password
        )
        st.success("Connexion enregistrée avec succès.")
        # Pour éviter boucle infinie, préfère ici ne pas faire un st.rerun automatique
