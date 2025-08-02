# app.py

import streamlit as st
import re
import pandas as pd
import stripe
import os

# Configuration initiale
st.set_page_config(layout="wide", page_title="Odoo AI Transformer", page_icon="🤖")

# Importations internes
from utils.db import init_db, load_connections, get_or_create_user, update_user_subscription, engine
from utils.security import FERNET, generate_and_display_key, SAVED_PASSWORD_PLACEHOLDER, sanitize_for_gcs
from utils.odoo import attempt_connection, extract_and_process_odoo_data
from services.openai_service import generate_transformation_plan, generate_looker_studio_instructions
from services.gcp_service import generate_gcp_function_code, generate_bigquery_view_code
from utils.auth_service import sign_up, sign_in, get_user_profile

# Test base de données
if engine is None:
    st.error("Échec de la création du moteur de la base de données. L'application ne peut pas démarrer.")
    st.stop()

try:
    connection = engine.connect()
    connection.close()
except Exception as e:
    st.error(f"Test de connexion à la base de données échoué : {e}")
    st.stop()

# Initialisation base
init_db()

# Vérification des secrets
required_secrets = ["OPENAI_API_KEY", "WEB_API_KEY", "stripe", "firebase_service_account", "database"]
if not all(st.secrets.get(key) for key in required_secrets):
    st.error("Un ou plusieurs secrets sont manquants dans `secrets.toml`.")
    st.stop()
if not FERNET:
    generate_and_display_key()
    st.stop()

# Authentification
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

st.sidebar.header("Authentification")

if st.session_state.user_info:
    user_email = st.session_state.user_info['email']
    st.sidebar.write(f"Connecté : **{user_email}**")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.user_info = None
        st.session_state.connection_success = False
        st.rerun()
else:
    nav = st.sidebar.radio("Navigation", ["Se connecter", "S'inscrire"])
    if nav == "Se connecter":
        with st.sidebar.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter"):
                try:
                    user_info = sign_in(email, password)
                    st.session_state.user_info = user_info
                    st.rerun()
                except Exception as e:
                    st.error(e)
    else:
        with st.sidebar.form("register_form"):
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            confirm = st.text_input("Confirmez le mot de passe", type="password")
            if st.form_submit_button("S'inscrire"):
                if password != confirm:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(password) < 6:
                    st.error("Mot de passe trop court.")
                else:
                    try:
                        sign_up(email, password)
                        st.success("Inscription réussie. Vérifiez votre email.")
                    except Exception as e:
                        st.error(e)

# Vérification email
if st.session_state.user_info is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

if not st.session_state.user_info['email_verified']:
    st.warning("Veuillez vérifier votre email.")
    if st.button("J'ai vérifié, rafraîchir"):
        token = st.session_state.user_info.get("idToken")
        if token:
            st.session_state.user_info = get_user_profile(token)
            st.rerun()
    st.stop()

# Utilisateur connecté
user_id = st.session_state.user_info['uid']
user_email = st.session_state.user_info['email']
user_db_data = get_or_create_user(user_id, user_email) or {}

# Stripe + Abonnement
stripe.api_key = st.secrets["stripe"]["secret_key"]
BASE_URL = "https://odoo-ai-transformer-app-421844406357.europe-west9.run.app"

if "session_id" in st.query_params:
    sid = st.query_params["session_id"]
    try:
        session = stripe.checkout.Session.retrieve(sid)
        if session.payment_status == "paid" and session.metadata.get("user_id") == user_id:
            update_user_subscription(user_id, "active")
            st.success("Merci pour votre abonnement !")
            st.query_params.clear()
            user_db_data = get_or_create_user(user_id, user_email)
    except Exception as e:
        st.error(f"Erreur Stripe : {e}")

if user_db_data.get("subscription_status") != "active":
    st.warning("Abonnement requis pour utiliser l'application.")
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': st.secrets["stripe"]["price_id"], 'quantity': 1}],
            mode='subscription',
            success_url=BASE_URL + "/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=BASE_URL,
            customer_email=user_email,
            metadata={'user_id': user_id}
        )
        st.link_button("S'abonner (30€/mois)", checkout_session.url)
    except Exception as e:
        st.error(e)
    st.stop()

# Connexion Odoo
st.sidebar.divider()
st.sidebar.header("🔌 Connexion Odoo")

connections = load_connections(user_id)
conn_names = ["Nouvelle connexion..."] + [c["name"] for c in connections]
if "selected_connection" not in st.session_state:
    st.session_state.selected_connection = conn_names[0]

def on_connection_change():
    name = st.session_state.connection_selector
    if name != "Nouvelle connexion...":
        selected = next((c for c in connections if c["name"] == name), None)
        if selected:
            st.session_state.url_input = selected["url"]
            st.session_state.db_input = selected["db_name"]
            st.session_state.username_input = selected["username"]
            st.session_state.password_input = SAVED_PASSWORD_PLACEHOLDER
    else:
        st.session_state.url_input = st.session_state.db_input = st.session_state.username_input = st.session_state.password_input = ""

st.sidebar.selectbox("Connexion Odoo", conn_names, key="connection_selector", on_change=on_connection_change)
st.sidebar.text_input("URL", key="url_input")
st.sidebar.text_input("Base de données", key="db_input")
st.sidebar.text_input("Email utilisateur", key="username_input")
st.sidebar.text_input("Mot de passe / API", type="password", key="password_input")
st.sidebar.button("Se connecter / Mettre à jour", on_click=attempt_connection, args=(user_id,))

if not st.session_state.get("connection_success"):
    st.info("Connectez une base Odoo pour commencer.")
    st.stop()

# Étape 1 : formulaire utilisateur
st.header("1. Décrire l'objectif de la transformation")
with st.form("prompt_form"):
    sujet = st.text_input("Sujet de l'analyse", key="form_sujet")
    col1, col2 = st.columns(2)
    with col1:
        metriques = st.text_area("Métriques", key="form_metriques")
        filtres = st.text_area("Filtres", key="form_filtres")
    with col2:
        groupes = st.text_area("Groupement", key="form_groupes")
        calculs = st.text_area("Calculs", key="form_calculs")
    uploaded_file = st.file_uploader("Fichier PDF/TXT optionnel", type=['pdf', 'txt'])
    if st.form_submit_button("Générer le plan"):
        prompt = "\n\n".join([
            f"## Objectif\n{sujet}" if sujet else "",
            f"## Métriques\n{metriques}" if metriques else "",
            f"## Filtres\n{filtres}" if filtres else "",
            f"## Groupement\n{groupes}" if groupes else "",
            f"## Calculs\n{calculs}" if calculs else ""
        ])
        st.session_state.assembled_user_prompt = prompt
        st.session_state.default_gcp_name = sanitize_for_gcs(sujet)
        if not prompt and not uploaded_file:
            st.warning("Veuillez remplir au moins un champ ou fournir un fichier.")
        else:
            generate_transformation_plan(prompt, uploaded_file)

# Étape 2 : affichage plan et exécution
if st.session_state.get("ai_python_code"):
    st.header("2. Valider le plan de transformation")
    st.json(st.session_state.ai_models_fields)
    st.code(st.session_state.ai_python_code, language="python")
    if st.button("▶️ Exécuter le plan"):
        try:
            dfs = extract_and_process_odoo_data(st.session_state.models_proxy, st.session_state.conn_details, st.session_state.ai_models_fields)
            exec_scope = {'pd': pd, 'dfs': dfs}
            exec(st.session_state.ai_python_code, exec_scope)
            if 'transform_data' not in exec_scope:
                st.error("Fonction `transform_data` manquante."); st.stop()
            st.session_state.transformed_df = exec_scope['transform_data'](dfs)
            st.success("Transformation effectuée.")
        except Exception as e:
            st.error(f"Erreur lors de l'exécution : {e}")
            st.stop()

# Étape 3 : Affichage des résultats et déploiement
if st.session_state.get("transformed_df") is not None:
    st.header("3. Résultat & déploiement")
    st.dataframe(st.session_state.transformed_df)
    col1, col2 = st.columns(2)
    with col1:
        pid = st.text_input("ID Projet GCP", st.secrets["firebase_service_account"].get("project_id", ""), key="gcp_project_id")
    with col2:
        prefix = st.text_input("Nom du fichier", st.session_state.default_gcp_name, key="gcp_file_name")
    if st.button("Générer fichiers de déploiement"):
        dataset_id = re.sub(r"[^a-zA-Z0-9_]", "_", st.session_state.conn_details["db"])
        view_name = f"v_{prefix}"
        st.subheader("main.py")
        st.code(generate_gcp_function_code(
            url=st.session_state.conn_details["url"],
            db=st.session_state.conn_details["db"],
            username=st.session_state.conn_details["username"],
            project_id=pid,
            file_name_prefix=prefix,
            model_fields_dict=st.session_state.ai_models_fields,
            ai_python_code=st.session_state.ai_python_code
        ), language="python")
        st.subheader("requirements.txt")
        st.code("pandas\ngoogle-cloud-storage\ngoogle-cloud-secret-manager", language="text")
        st.subheader("view.sql")
        st.code(generate_bigquery_view_code(pid, dataset_id, view_name, prefix), language="sql")
        st.subheader("Commande gcloud : création secret")
        st.code(f'echo -n "{st.session_state.conn_details["password"]}" | gcloud secrets create api_key_{dataset_id} --project={pid} --replication-policy="automatic" --data-file=-', language="bash")
        with st.spinner("Génération des instructions Looker Studio..."):
            try:
                df = st.session_state.transformed_df
                schema = {c: str(t) for c, t in df.dtypes.items()}
                instructions = generate_looker_studio_instructions(
                    st.session_state.assembled_user_prompt,
                    str(schema),
                    f"{pid}.{dataset_id}.{view_name}"
                )
                st.markdown(instructions, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erreur Looker Studio : {e}")
