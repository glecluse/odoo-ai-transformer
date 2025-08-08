# Application.py

import streamlit as st
import pandas as pd
import re
import json
import traceback
import xmlrpc.client
import os

# Import des modules locaux
import database as db
import odoo
import ai_services
import gcp
import utils
import kms_services

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Odoo AI Transformer - App", page_icon="🚀")

# --- Gardien d'Authentification ---
if not st.session_state.get('is_logged_in', False):
    st.error("🔒 Accès non autorisé. Veuillez vous connecter pour utiliser l'application.")
    st.page_link("app.py", label="Retour à l'accueil", icon="🏠")
    st.stop()

# --- Initialisation de la base de données ---
db.init_db()

# --- Initialisation du st.session_state ---
for key in [
    'connection_success', 'models', 'model_fields', 'ai_models_fields', 'ai_python_code', 
    'transformed_df', 'conversation_history', 'conn_details', 'password_to_use', 'models_proxy',
    'user_prompt_for_viz', 'viz_guide', 'gcp_code_generated'
]:
    if key not in st.session_state:
        st.session_state[key] = {} if key.endswith('s') or key == 'conn_details' else None
        if key == 'conversation_history': 
            st.session_state[key] = []
        if key == 'gcp_code_generated':
            st.session_state[key] = False

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.header("🔌 Connexion Odoo")
    connections = db.load_connections()
    connection_names = ["Nouvelle connexion..."] + [c['name'] for c in connections]
    
    def on_connection_change():
        selected_name = st.session_state.connection_selector
        st.session_state.password_input = "" 
        if selected_name != "Nouvelle connexion...":
            selected_conn_data = next((c for c in connections if c['name'] == selected_name), None)
            if selected_conn_data:
                st.session_state.url_input = selected_conn_data['url']
                st.session_state.db_input = selected_conn_data['db_name']
                st.session_state.username_input = selected_conn_data['username']
                st.session_state.conn_details = selected_conn_data
        else:
            st.session_state.url_input = ""
            st.session_state.db_input = ""
            st.session_state.username_input = ""
            st.session_state.conn_details = {}
        st.session_state.selected_connection = selected_name
        # Réinitialiser le flot à chaque changement de connexion
        st.session_state.connection_success = False
        st.session_state.transformed_df = None
        st.session_state.gcp_code_generated = False
        st.session_state.viz_guide = None

    st.selectbox("Connexions sauvegardées", connection_names, key='connection_selector', on_change=on_connection_change)
    st.text_input("URL Odoo", key='url_input')
    st.text_input("Base de données", key='db_input')
    st.text_input("Utilisateur (email)", key='username_input')
    st.text_input("Mot de passe / Clé API", type="password", key='password_input', help="Laissez vide si vous utilisez une connexion sauvegardée.")
    st.button("Se connecter", on_click=odoo.attempt_connection)

# --- INTERFACE PRINCIPALE ---
st.title("🚀 Application Odoo AI Data Transformer")

if not st.session_state.get('connection_success'):
    st.info("👋 Veuillez vous connecter à votre instance Odoo via le menu à gauche pour commencer.")
else:
    current_connection_name = st.session_state.get('conn_details', {}).get('name')
    user_is_authorized = db.is_connection_authorized(
        user_id=st.session_state.get('firebase_uid'),
        connection_name=current_connection_name
    )

    if user_is_authorized:
        st.success(f"Accès autorisé pour la connexion '{current_connection_name}'. Toutes les fonctionnalités sont disponibles.")
        st.warning("⚠️ **Avertissement de sécurité :** Cette application exécute du code généré par une IA. Vérifiez toujours le code avant de l'exécuter dans un environnement de production.", icon="🛡️")
        
        st.header("1. Décrire l'objectif de l'extraction")
        with st.form(key="prompt_form"):
            st.subheader("Formulaire Guidé pour l'IA")
            title = st.text_input("Titre du rapport", help="Ex: 'Analyse des ventes trimestrielles'")
            subject = st.text_input("Sujet principal (Que doit représenter chaque ligne ?)", help="Ex: 'une facture', 'un client'")
            columns = st.text_area("Colonnes souhaitées", height=100, help="Ex: 'nom du client, date de la facture, montant total HT'")
            filters = st.text_area("Filtres et conditions", height=100, help="Ex: 'uniquement les factures de l'année 2024'")
            calculations = st.text_area("Calculs ou agrégations (Optionnel)", height=100, help="Ex: 'somme des ventes par commercial'")
            sorting = st.text_input("Tri des résultats (Optionnel)", help="Ex: 'par date décroissante'")
            submitted = st.form_submit_button("🤖 Générer le plan de transformation")

        if submitted:
            if not all([title, subject, columns]):
                st.warning("Veuillez remplir au moins les champs 'Titre', 'Sujet principal' et 'Colonnes'.")
            else:
                user_prompt = f"Titre du rapport: {title}\nLe sujet principal est: {subject}\nJe veux les colonnes suivantes: {columns}\nApplique ces filtres: {filters}\nFais ces calculs: {calculations}\nEt trie les résultats par: {sorting}"
                st.session_state.user_prompt_for_viz = user_prompt
                with st.spinner("Génération du plan de transformation..."):
                    ai_plan = ai_services.get_ai_plan(user_prompt)
                if ai_plan:
                    st.session_state.ai_models_fields = ai_plan.get('models_and_fields')
                    st.session_state.ai_python_code = ai_plan.get('python_code')
                    st.session_state.transformed_df = None
                    st.session_state.gcp_code_generated = False
                    st.session_state.viz_guide = None
                    st.success("Plan de transformation généré avec succès !")
        
        if st.session_state.get('ai_python_code'):
            st.divider()
            st.header("2. Valider et exécuter la transformation")
            with st.expander("🔍 Plan de transformation de l'IA", expanded=True):
                st.write("**L'IA a généré le plan suivant :**")
                st.json(st.session_state.ai_models_fields)
                st.code(st.session_state.ai_python_code, language='python')

            if st.button("▶️ Exécuter le plan (Extraction + Transformation)"):
                dataframes = {}
                st.info("Démarrage de l'extraction optimisée des données Odoo...")
                try:
                    total_models = len(st.session_state.ai_models_fields)
                    model_count = 0
                    for model_name, fields in st.session_state.ai_models_fields.items():
                        model_count += 1
                        st.write(f"---")
                        st.write(f"**Modèle {model_count}/{total_models} : `{model_name}`**")
                        list_of_chunks = []
                        total_rows_for_model = 0
                        progress_bar = st.progress(0, text=f"Initialisation de l'extraction pour `{model_name}`...")
                        
                        data_generator = odoo.get_large_dataset_paginated(
                            models_proxy=st.session_state.models_proxy, 
                            db=st.session_state.conn_details['db'], 
                            uid=st.session_state.uid, 
                            password=st.session_state.password_to_use,
                            model_name=model_name, 
                            domain=[], 
                            fields=fields, 
                            chunk_size=2000
                        )
                        
                        for i, df_chunk in enumerate(data_generator):
                            if not df_chunk.empty:
                                list_of_chunks.append(df_chunk)
                                total_rows_for_model += len(df_chunk)
                                progress_bar.progress(max(0.0, (i % 50) / 49.0), text=f"Extraction de `{model_name}`... {total_rows_for_model} lignes reçues.")
                        
                        progress_bar.progress(1.0, text=f"Extraction de `{model_name}` terminée. {total_rows_for_model} lignes au total.")
                        
                        if list_of_chunks:
                            dataframes[model_name] = pd.concat(list_of_chunks, ignore_index=True)
                        else:
                            dataframes[model_name] = pd.DataFrame(columns=fields)
                    st.success("Toutes les données brutes ont été extraites avec succès.")
                except Exception as e:
                    st.error(f"Erreur durant l'extraction des données Odoo : {e}")
                    st.stop()
                
                if dataframes:
                    with st.spinner("Exécution du code de transformation de l'IA..."):
                        result_df = ai_services.run_ai_code(st.session_state.ai_python_code, dataframes)
                        if result_df is not None:
                            st.session_state.transformed_df = result_df
                            st.success("Transformation par l'IA réussie !")
                        else:
                            st.error("L'exécution du code de l'IA n'a retourné aucun résultat.")

        if st.session_state.get('transformed_df') is not None:
            st.divider()
            st.header("3. Déployer les artefacts sur Google Cloud")
            st.subheader("Aperçu du résultat de la transformation :")
            st.dataframe(st.session_state.transformed_df)
            st.text_input("Nom de base pour les fichiers et la vue GCP :", key="gcp_file_name_input")
            
            if st.button("✅ Valider et Générer le code GCP"):
                file_name_prefix = st.session_state.gcp_file_name_input
                if file_name_prefix:
                    try:
                        active_subs = db.get_active_subscriptions(st.session_state.get('firebase_uid'))
                        current_subscription = active_subs.get(current_connection_name)
                        if not current_subscription or 'license_key' not in current_subscription:
                            st.error("Impossible de trouver une clé de licence valide pour cet abonnement.")
                            st.stop()
                        license_key = current_subscription['license_key']

                        with st.spinner("Génération du code de déploiement..."):
                            project_id = os.getenv("PROJECT_ID", "odoo-ai-transformer") 
                            dataset_id = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state.conn_details.get('db', 'odoo_dataset'))
                            view_name = f"v_{file_name_prefix}"
                            
                            st.subheader("A. Cloud Function (`main.py`)")
                            function_code = gcp.generate_gcp_function_code(
                                url=st.session_state.conn_details['url'], 
                                db=st.session_state.conn_details['db'], 
                                username=st.session_state.conn_details['username'], 
                                file_name_prefix=file_name_prefix, 
                                model_fields_dict=st.session_state.ai_models_fields, 
                                ai_python_code=st.session_state.ai_python_code,
                                license_key=license_key
                            )
                            st.code(function_code, language="python")

                            st.subheader("B. Commande gcloud (création du secret Odoo)")
                            decrypted_password = kms_services.decrypt_password(st.session_state.conn_details['encrypted_password'])
                            secret_name_odoo = f"api_key_{dataset_id.replace('-', '_')}"
                            st.code(f'echo -n "{decrypted_password}" | gcloud secrets create {secret_name_odoo} --replication-policy="automatic" --data-file=-', language="bash")
                            st.warning("⚠️ Clé API exposée ! N'exécutez cette commande que dans un terminal sécurisé et une seule fois.", icon="🔒")

                            st.subheader("C. Dépendances (`requirements.txt`)")
                            st.code("pandas\ngoogle-cloud-storage\ngoogle-cloud-secret-manager\nrequests", language="text")

                            st.subheader("D. Vue BigQuery (`view.sql`)")
                            st.code(gcp.generate_bigquery_view_code(project_id, dataset_id, view_name, file_name_prefix), language="sql")
                        
                        st.success("Artefacts GCP générés.")
                        st.session_state.gcp_code_generated = True
                    except Exception as e:
                        st.error(f"Une erreur inattendue est survenue : {e}")
                        print(f"--- ERROR in GCP code generation ---\n{traceback.format_exc()}")
                else:
                    st.warning("Veuillez donner un nom de base avant de générer le code.")
        
        if st.session_state.get('gcp_code_generated'):
            st.divider()
            st.header("4. Assistant de Visualisation (via IA)")
            
            st.info("Choisissez votre outil de Business Intelligence pour obtenir un guide de création sur mesure.")
            
            tool_choice = st.selectbox(
                "Quel outil de visualisation souhaitez-vous utiliser ?",
                ("Looker Studio", "Microsoft Power BI","Metabase","Qlik Sense / QlikView","Sisense", "Tableau"),
                key="viz_tool_choice"
            )

            if st.button(f"📖 Générer le guide pour {tool_choice}"):
                with st.spinner(f"L'IA rédige le guide pas à pas pour {tool_choice}..."):
                    project_id = os.getenv("PROJECT_ID", "odoo-ai-transformer")
                    dataset_id = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state.conn_details.get('db', 'odoo_dataset'))
                    view_name = f"v_{st.session_state.gcp_file_name_input}"
                    
                    guide_context = {
                        "user_goal": st.session_state.user_prompt_for_viz,
                        "tool": tool_choice,
                        "chart_type": "le graphique le plus pertinent pour l'objectif", # L'IA déterminera le meilleur type de graphique
                        "columns": list(st.session_state.transformed_df.columns),
                        "project_id": project_id,
                        "dataset_id": dataset_id,
                        "view_name": view_name
                    }
                    
                    guide = ai_services.get_ai_visualization_guide(guide_context)
                    st.session_state.viz_guide = guide

            if st.session_state.get('viz_guide'):
                st.subheader(f"📋 Votre Guide de Visualisation pour {st.session_state.viz_tool_choice}")
                st.markdown(st.session_state.viz_guide, unsafe_allow_html=True)

    else:
        st.error(f"🚫 Abonnement ou accès gratuit requis pour la connexion '{current_connection_name}'.")
        st.warning("Pour extraire des données et utiliser l'IA avec cette connexion, veuillez activer un abonnement.")
        st.page_link("pages/5_Abonnement.py", label="Gérer mes abonnements", icon="💳")