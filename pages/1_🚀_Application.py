import streamlit as st
import pandas as pd
import re
import json

# Import des modules locaux
import database as db
import odoo
import ai_services
import gcp
import utils

# --- CONFIGURATION DE LA PAGE ET INITIALISATION ---
st.set_page_config(layout="wide", page_title="Odoo AI Transformer", page_icon="🤖")

# Appel pour s'assurer que la table DB existe au démarrage
db.init_db()

# Initialisation du st.session_state
for key in ['connection_success', 'models', 'model_fields', 'ai_models_fields', 'ai_python_code', 'transformed_df', 'conversation_history', 'conn_details']:
    if key not in st.session_state:
        st.session_state[key] = None if not key.endswith('s') else {}
        if key == 'conversation_history': st.session_state[key] = []
        if key == 'conn_details': st.session_state[key] = {} # Assurer que c'est un dict

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.header("🔌 Connexion Odoo")
    connections = db.load_connections()
    connection_names = ["Nouvelle connexion..."] + [c['name'] for c in connections]
    
    if 'selected_connection' not in st.session_state:
        st.session_state.selected_connection = connection_names[0]

    # --- La logique de cette fonction est modifiée ---
    def on_connection_change():
        selected_name = st.session_state.connection_selector
        st.session_state.password_input = "" # Vider le champ mot de passe à chaque changement

        if selected_name != "Nouvelle connexion...":
            selected_conn_data = next((c for c in connections if c['name'] == selected_name), None)
            if selected_conn_data:
                # Remplir les champs du formulaire
                st.session_state.url_input = selected_conn_data['url']
                st.session_state.db_input = selected_conn_data['db_name']
                st.session_state.username_input = selected_conn_data['username']
                
                # Pré-charger les détails de connexion, y compris la clé chiffrée
                st.session_state.conn_details = selected_conn_data
        else:
            # Réinitialiser les champs et les détails de connexion
            st.session_state.url_input = ""
            st.session_state.db_input = ""
            st.session_state.username_input = ""
            st.session_state.conn_details = {} # Vider les détails
        
        st.session_state.selected_connection = selected_name
        # On ne veut pas déclencher une tentative de connexion automatique
        st.session_state.connection_success = False


    st.selectbox("Connexions sauvegardées", connection_names, key='connection_selector', on_change=on_connection_change)
    st.text_input("URL Odoo", key='url_input')
    st.text_input("Base de données", key='db_input')
    st.text_input("Utilisateur (email)", key='username_input')
    st.text_input("Mot de passe / Clé API", type="password", key='password_input', help="Laissez vide si vous utilisez une connexion sauvegardée. Remplissez pour enregistrer une nouvelle connexion ou pour mettre à jour une clé API existante.")
    st.button("Se connecter", on_click=odoo.attempt_connection)


# --- INTERFACE PRINCIPALE (Aucun changement dans cette partie) ---
st.title("🤖 Odoo AI Data Transformer")

if not st.session_state.get('connection_success'):
    st.info("👋 Bienvenue ! Connectez-vous à votre instance Odoo via le menu à gauche.")
else:
    # --- 1. GÉNÉRATION DU PLAN ---
    st.warning("⚠️ **Avertissement de sécurité :** Cette application exécute du code généré par une IA.")
    st.header("1. Décrire l'objectif et générer le plan")
    user_prompt = st.text_area("Décrivez le tableau final que vous voulez obtenir...", height=100, key="main_prompt")
    uploaded_file = st.file_uploader("Ou téléchargez un document (PDF, TXT)...", type=['pdf', 'txt'])

    if st.button("🤖 Générer le plan de transformation"):
        if not user_prompt and not uploaded_file:
            st.warning("Veuillez décrire votre objectif ou télécharger un document.")
        else:
            document_text = utils.read_uploaded_file(uploaded_file)
            if document_text is not None:
                try:
                    ai_plan = ai_services.get_ai_plan(user_prompt, document_text)
                    st.session_state.ai_models_fields = ai_plan['models_and_fields']
                    st.session_state.ai_python_code = ai_plan['python_code']
                    st.session_state.transformed_df = None # Réinitialiser le résultat précédent
                except Exception as e:
                    st.error(f"Erreur lors de la génération du plan par l'IA : {e}")
                    # Affichez la réponse de l'IA si elle est disponible pour le débogage
                    if 'ai_response_text' in locals():
                        st.code(ai_response_text, language='text')

    # --- 2. VALIDATION ET EXÉCUTION ---
    if st.session_state.get('ai_python_code'):
        st.divider()
        st.header("2. Valider le plan et exécuter")
        
        with st.expander("🔍 Plan de transformation de l'IA", expanded=True):
            st.write("**L'IA a généré le plan suivant :**")
            st.json(st.session_state.ai_models_fields)
            st.code(st.session_state.ai_python_code, language='python')

        if st.button("▶️ Exécuter le plan (Extraction + Transformation)"):
            with st.spinner("Extraction des données Odoo en cours..."):
                dataframes = odoo.extract_data_from_odoo(st.session_state.ai_models_fields)
            
            if dataframes:
                st.success("Données brutes extraites.")
                with st.spinner("Exécution du code de transformation de l'IA..."):
                    result_df = ai_services.run_ai_code(st.session_state.ai_python_code, dataframes)
                    if result_df is not None:
                        st.session_state.transformed_df = result_df
                        st.success("Transformation par l'IA réussie !")

    # --- 3. RÉSULTAT ET DÉPLOIEMENT ---
    if st.session_state.get('transformed_df') is not None:
        st.divider()
        st.header("3. Résultat et déploiement")
        st.dataframe(st.session_state.transformed_df)
        
        col_gcp1, col_gcp2 = st.columns(2)
        with col_gcp1:
             file_name_prefix = st.text_input("Nom de base pour les fichiers et la vue GCP :", key="gcp_file_name")
        with col_gcp2:
             if st.button("✅ Valider et Générer le code GCP"):
                if file_name_prefix:
                     # ... la logique de génération GCP reste la même
                     pass