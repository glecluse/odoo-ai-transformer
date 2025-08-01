# Fichier : utils/odoo.py
import streamlit as st
import xmlrpc.client
import pandas as pd
from utils.db import save_connection, load_connections
from utils.security import SAVED_PASSWORD_PLACEHOLDER, decrypt_data

def attempt_connection(user_id: str): # user_id est maintenant requis
    url, db, username, password = st.session_state.url_input, st.session_state.db_input, st.session_state.username_input, st.session_state.password_input
    
    if not user_id:
        st.error("Erreur : session utilisateur invalide.")
        return

    if password == SAVED_PASSWORD_PLACEHOLDER: password = ""
    if not password:
        selected_name = st.session_state.get('connection_selector')
        if selected_name and selected_name != "Nouvelle connexion...":
            connections = load_connections(user_id)
            selected_conn_data = next((c for c in connections if c['name'] == selected_name), None)
            if selected_conn_data and selected_conn_data.get('password_encrypted'):
                decrypted_pass = decrypt_data(selected_conn_data['password_encrypted'])
                if decrypted_pass:
                    password = decrypted_pass
                    st.info("Utilisation de la clé API sauvegardée.")
                else:
                    st.error("Impossible de déchiffrer la clé API. Votre FERNET_KEY a-t-elle changé ?"); return
    
    if not all([url, db, username, password]):
        st.error("Veuillez remplir tous les champs de connexion, y compris la clé API."); return
    
    with st.spinner("Connexion à Odoo..."):
        try:
            clean_url = url.rstrip('/')
            common = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/common')
            uid = common.authenticate(db, username, password, {})
            if uid:
                models_proxy = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/object')
                st.session_state.update(models_proxy=models_proxy, uid=uid, conn_details={'url': url, 'db': db, 'username': username, 'password': password, 'uid': uid}, connection_success=True)
                connection_name = f"{db} ({username})"
                # La connexion est maintenant sauvegardée pour l'utilisateur spécifique
                save_connection(user_id, connection_name, url, db, username, password)
                st.success(f"Connexion '{connection_name}' réussie et sauvegardée.")
            else:
                st.error("Échec de l'authentification."); st.session_state.connection_success = False
        except Exception as e:
            st.error(f"Erreur de connexion : {e}"); st.session_state.connection_success = False

def extract_and_process_odoo_data(models_proxy, conn_details, models_to_extract):
    dataframes = {}
    for model_name, fields in models_to_extract.items():
        try:
            limit, offset, all_records = 5000, 0, []
            progress_message = st.empty()
            while True:
                data_batch = models_proxy.execute_kw(
                    conn_details['db'], conn_details['uid'], conn_details['password'],
                    model_name, 'search_read', [[]], {'fields': fields, 'limit': limit, 'offset': offset}
                )
                if not data_batch: break
                all_records.extend(data_batch)
                offset += limit
                progress_message.info(f"Chargement de {len(all_records)} lignes pour {model_name}...")
            processed_data = []
            for record in all_records:
                new_record = {}
                for field, value in record.items():
                    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
                        new_record[field] = value[0]
                    elif isinstance(value, (dict, list)):
                        new_record[field] = str(value)
                    else:
                        new_record[field] = value
                processed_data.append(new_record)
            df = pd.DataFrame(processed_data)
            dataframes[model_name] = df
            progress_message.empty()
        except Exception as e:
            st.error(f"Erreur lors de l'extraction de {model_name}: {e}")
            raise
    return dataframes