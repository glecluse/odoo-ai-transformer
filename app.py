import streamlit as st
import re
import pandas as pd
import stripe

# La configuration de la page est la première commande Streamlit exécutée
st.set_page_config(layout="wide", page_title="Odoo AI Transformer", page_icon="🤖")

# Importations depuis nos modules
from utils.db import init_db, load_connections, get_or_create_user, update_user_subscription
from utils.security import FERNET, generate_and_display_key, SAVED_PASSWORD_PLACEHOLDER, sanitize_for_gcs
from utils.odoo import attempt_connection, extract_and_process_odoo_data
from services.openai_service import generate_transformation_plan, generate_looker_studio_instructions
from services.gcp_service import generate_gcp_function_code, generate_bigquery_view_code
from utils.auth_service import sign_up, sign_in, get_user_profile

# --- CONFIGURATION ET INITIALISATION ---
init_db()

# Vérification des secrets au démarrage
if not all(st.secrets.get(key) for key in ["OPENAI_API_KEY", "WEB_API_KEY", "stripe", "firebase_service_account", "database"]):
    st.error("Un ou plusieurs secrets ne sont pas configurés dans votre fichier secrets.toml.")
    st.stop()
if not FERNET:
    generate_and_display_key()
    st.stop()

# Initialisation de l'état de session pour l'utilisateur
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- AUTHENTIFICATION ---
st.sidebar.header("Authentification")

if st.session_state.user_info:
    user_email = st.session_state.user_info['email']
    st.sidebar.write(f"Connecté : **{user_email}**")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.user_info = None
        st.session_state.connection_success = False
        st.rerun()
else:
    choice = st.sidebar.radio("Navigation", ["Se connecter", "S'inscrire"])
    if choice == "Se connecter":
        with st.sidebar.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            login_button = st.form_submit_button("Se connecter")
            if login_button:
                try:
                    user_info = sign_in(email, password)
                    st.session_state.user_info = user_info
                    st.rerun()
                except Exception as e:
                    st.error(e)
    else: # S'inscrire
        with st.sidebar.form("register_form"):
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            confirm_password = st.text_input("Confirmez le mot de passe", type="password")
            register_button = st.form_submit_button("S'inscrire")
            if register_button:
                if password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                else:
                    try:
                        sign_up(email, password)
                        st.success("Compte créé ! Un e-mail de vérification vous a été envoyé.")
                    except Exception as e:
                        st.error(f"Échec de l'inscription : {e}")


# --- CORPS DE L'APPLICATION (protégé par l'authentification) ---
if st.session_state.user_info is None:
    st.warning("Veuillez vous connecter ou vous inscrire pour utiliser l'application.")
    st.stop()

if not st.session_state.user_info['email_verified']:
    st.warning("Votre e-mail n'a pas encore été vérifié. Veuillez cliquer sur le lien qui vous a été envoyé.")
    st.info("Une fois que vous avez cliqué sur le lien, cliquez sur le bouton ci-dessous.")
    if st.button("J'ai vérifié mon e-mail, rafraîchir mon statut"):
        id_token = st.session_state.user_info.get("idToken")
        if id_token:
            st.session_state.user_info = get_user_profile(id_token)
            st.rerun()
    st.stop()

# L'utilisateur est connecté ET vérifié, on peut continuer
user_id = st.session_state.user_info['uid']
user_email = st.session_state.user_info['email']
user_db_data = get_or_create_user(user_id, user_email)

# --- VÉRIFICATION DE L'ABONNEMENT ---
stripe.api_key = st.secrets["stripe"]["secret_key"]

# ### NOUVEAU ### : Définition de l'URL de base de votre application
BASE_URL = "https://odoo-ai-transformer-app-421844406357.europe-west9.run.app"

if "session_id" in st.query_params:
    session_id = st.query_params["session_id"]
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            retrieved_user_id = session.metadata.get('user_id')
            if retrieved_user_id == user_id:
                update_user_subscription(user_id, "active")
                st.success("Merci pour votre abonnement ! L'application est maintenant débloquée.")
                st.info("Vous pouvez maintenant connecter votre base Odoo.")
                user_db_data = get_or_create_user(user_id, user_email)
                st.query_params.clear()
    except Exception as e:
        st.error(f"Erreur lors de la vérification de la session de paiement : {e}")

if user_db_data.get("subscription_status") != "active":
    st.warning("Vous devez être abonné pour utiliser cette fonctionnalité.")
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': st.secrets["stripe"]["price_id"], 'quantity': 1}],
            mode='subscription',
            success_url=BASE_URL + "/?session_id={CHECKOUT_SESSION_ID}", # Utilise la nouvelle URL
            cancel_url=BASE_URL, # Utilise la nouvelle URL
            customer_email=user_email,
            metadata={'user_id': user_id}
        )
        st.link_button("S'abonner (30€/mois)", checkout_session.url)
    except Exception as e:
        st.error(f"Erreur de connexion avec Stripe : {e}")
    st.stop()

# --- APPLICATION PRINCIPALE (accessible uniquement aux abonnés) ---
st.success("Abonnement actif. Bienvenue !")

with st.sidebar:
    st.divider()
    st.header("🔌 Connexion Odoo")
    connections = load_connections(user_id)
    connection_names = ["Nouvelle connexion..."] + [c['name'] for c in connections]
    if 'selected_connection' not in st.session_state: st.session_state.selected_connection = connection_names[0]
    
    def on_connection_change():
        selected_name = st.session_state.connection_selector
        if selected_name != "Nouvelle connexion...":
            connections_list = load_connections(user_id)
            selected_conn_data = next((c for c in connections_list if c['name'] == selected_name), None)
            if selected_conn_data:
                st.session_state.url_input, st.session_state.db_input, st.session_state.username_input = selected_conn_data['url'], selected_conn_data['db_name'], selected_conn_data['username']
                st.session_state.password_input = SAVED_PASSWORD_PLACEHOLDER if selected_conn_data.get('password_encrypted') else ""
        else:
            st.session_state.url_input, st.session_state.db_input, st.session_state.username_input, st.session_state.password_input = "", "", "", ""
        st.session_state.selected_connection = selected_name

    st.selectbox("Connexions sauvegardées", connection_names, key='connection_selector', on_change=on_connection_change)
    st.text_input("URL Odoo", key='url_input')
    st.text_input("Base de données", key='db_input')
    st.text_input("Utilisateur (email)", key='username_input')
    st.text_input("Mot de passe / Clé API", type="password", key='password_input', help="Laissez vide pour utiliser la clé sauvegardée.")
    st.button("Se connecter / Mettre à jour", on_click=attempt_connection, args=(user_id,))

if not st.session_state.get('connection_success'):
    st.info("👋 Bienvenue ! Connectez-vous à une instance Odoo via le menu de gauche pour commencer.")
else:
    st.header("1. Décrire l'objectif de la transformation")
    with st.form("prompt_form"):
        sujet_principal = st.text_input("Sujet principal de l'analyse", key="form_sujet", help="Ex: 'Analyse mensuelle du chiffre d'affaires par commercial'.")
        col1, col2 = st.columns(2)
        with col1:
            metriques = st.text_area("Métriques et agrégations", key="form_metriques", help="Ex:\n- Somme du montant total\n- Nombre de commandes uniques")
            filtres = st.text_area("Filtres à appliquer", key="form_filtres", help="Ex:\n- Uniquement les commandes de 2024\n- Exclure les commandes annulées")
        with col2:
            groupes = st.text_area("Regrouper les résultats par", key="form_groupes", help="Ex:\n- Par mois\n- Par commercial")
            calculs_speciaux = st.text_area("Calculs ou transformations spéciales", key="form_calculs", help="Ex:\n- Calculer la marge\n- Extraire l'année de la date")
        uploaded_file = st.file_uploader("Optionnel : Télécharger un document de contexte (PDF, TXT)...", type=['pdf', 'txt'])
        submitted = st.form_submit_button("🤖 Générer le plan de transformation")

    if submitted:
        prompt_parts = []
        if st.session_state.form_sujet: prompt_parts.append(f"## Objectif Principal\n{st.session_state.form_sujet}")
        if st.session_state.form_metriques: prompt_parts.append(f"## Métriques et Agrégations\n{st.session_state.form_metriques}")
        if st.session_state.form_groupes: prompt_parts.append(f"## Dimensions de Groupement\n{st.session_state.form_groupes}")
        if st.session_state.form_filtres: prompt_parts.append(f"## Filtres\n{st.session_state.form_filtres}")
        if st.session_state.form_calculs: prompt_parts.append(f"## Calculs Spéciaux\n{st.session_state.form_calculs}")
        user_prompt = "\n\n".join(prompt_parts)
        st.session_state.assembled_user_prompt = user_prompt
        st.session_state.default_gcp_name = sanitize_for_gcs(st.session_state.form_sujet)
        if not user_prompt and not uploaded_file:
            st.warning("Veuillez remplir le formulaire ou télécharger un document.")
        else:
            generate_transformation_plan(user_prompt, uploaded_file)

    if st.session_state.get('ai_python_code'):
        st.divider()
        st.header("2. Valider le plan et exécuter")
        with st.expander("🔍 Plan de transformation de l'IA", expanded=True):
            st.write("**L'IA a généré le plan suivant :**")
            st.json(st.session_state.ai_models_fields)
            st.code(st.session_state.ai_python_code, language='python')
        st.warning("️️️⚠️ **Attention** : Vous allez exécuter le code Python ci-dessus, généré par une IA.")
        if st.button("▶️ Exécuter le plan (Extraction + Transformation)"):
            try:
                with st.spinner("Extraction des données en cours..."):
                    dataframes = extract_and_process_odoo_data(st.session_state.models_proxy, st.session_state.conn_details, st.session_state.ai_models_fields)
                    st.session_state.dataframes = dataframes
                    st.success("Données brutes extraites.")
                with st.spinner("Exécution du code de transformation de l'IA..."):
                    code_to_run = st.session_state.ai_python_code
                    exec_scope = {'pd': pd, 'dfs': st.session_state.dataframes}
                    exec(code_to_run, exec_scope)
                    if 'transform_data' not in exec_scope:
                        st.error("Erreur critique : La fonction 'transform_data' est manquante."); st.stop()
                    transform_function = exec_scope['transform_data']
                    st.session_state.transformed_df = transform_function(st.session_state.dataframes.copy())
            except Exception as e:
                st.error(f"L'exécution a échoué : {e}"); st.stop()

    if st.session_state.get('transformed_df') is not None:
        st.divider()
        st.header("3. Résultat et déploiement sur Cloud Functions")
        st.dataframe(st.session_state.transformed_df)
        st.subheader("Générer les ressources de déploiement")
        col_gcp1, col_gcp2 = st.columns(2)
        with col_gcp1:
            project_id = st.text_input("ID du projet GCP", value=st.secrets.get("firebase_service_account", {}).get("project_id", "votre-projet-gcp"), key="gcp_project_id")
        with col_gcp2:
            default_name = st.session_state.get("default_gcp_name", "export-odoo")
            file_name_prefix = st.text_input("Nom de la fonction et des fichiers", value=default_name, key="gcp_file_name")
            
        if st.button("✅ Valider et Générer le package de déploiement"):
            if file_name_prefix and project_id:
                dataset_id = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state.conn_details.get('db', 'odoo'))
                view_name = f"v_{file_name_prefix}"
                full_view_name = f"{project_id}.{dataset_id}.{view_name}"
                st.subheader("A. Fichier principal (`main.py`)")
                st.code(generate_gcp_function_code(url=st.session_state.conn_details['url'], db=st.session_state.conn_details['db'], username=st.session_state.conn_details['username'], project_id=project_id, file_name_prefix=file_name_prefix, model_fields_dict=st.session_state.ai_models_fields, ai_python_code=st.session_state.ai_python_code), language="python")
                st.subheader("B. Dépendances (`requirements.txt`)")
                requirements_content = """pandas
google-cloud-storage
google-cloud-secret-manager"""
                st.code(requirements_content, language="text")
                st.subheader("C. Instructions de déploiement")
                st.markdown(f"""
1.  **Enregistrez** les deux blocs de code ci-dessus dans des fichiers `main.py` et `requirements.txt`.
2.  **Exécutez la commande `gcloud` suivante :**
""")
                gcloud_command = f"""gcloud functions deploy {file_name_prefix} \\
    --gen2 \\
    --runtime python311 \\
    --region europe-west1 \\
    --source . \\
    --entry-point odoo_etl_to_gcs \\
    --trigger-http \\
    --allow-unauthenticated"""
                st.code(gcloud_command, language="bash")
                st.markdown("""
3.  **Important :** Assurez-vous que le compte de service de votre fonction a bien le rôle **"Accesseur de secrets Secret Manager"**.
""")
                st.subheader("D. Vue BigQuery (`view.sql`)")
                st.code(generate_bigquery_view_code(project_id, dataset_id, view_name, file_name_prefix), language="sql")
                st.subheader("E. Commande gcloud (création du secret)")
                st.code(f'echo -n "{st.session_state.conn_details["password"]}" | gcloud secrets create api_key_{dataset_id.replace("-", "_")} --project={project_id} --replication-policy="automatic" --data-file=-', language="bash")
                st.warning("N'exécutez cette commande qu'une seule fois par secret.")
                st.subheader("F. Instructions pour Looker Studio")
                with st.spinner("🧠 L'IA génère les instructions pour Looker Studio..."):
                    try:
                        df = st.session_state.transformed_df
                        df_schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
                        instructions = generate_looker_studio_instructions(
                            st.session_state.assembled_user_prompt,
                            str(df_schema),
                            full_view_name
                        )
                        st.markdown(instructions, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Erreur lors de la génération des instructions Looker Studio : {e}")
            else:
                st.warning("Veuillez donner un nom de base et un ID de projet avant de générer le code.")