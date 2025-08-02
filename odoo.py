import streamlit as st
import xmlrpc.client
import pandas as pd
from database import save_connection

def attempt_connection():
    """Tente de se connecter à Odoo avec les informations fournies dans la session."""
    url = st.session_state.url_input
    db = st.session_state.db_input
    username = st.session_state.username_input
    password = st.session_state.password_input

    if not all([url, db, username, password]):
        st.error("Veuillez remplir tous les champs de connexion.")
        return

    with st.spinner("Connexion à Odoo..."):
        try:
            clean_url = url.rstrip('/')
            common = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/common')
            uid = common.authenticate(db, username, password, {})

            if uid:
                models_proxy = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/object')
                st.session_state.models_proxy = models_proxy
                st.session_state.uid = uid
                st.session_state.conn_details = {'url': url, 'db': db, 'username': username, 'password': password}
                st.session_state.connection_success = True

                # Sauvegarde de la connexion réussie
                connection_name = f"{db} ({username})"
                save_connection(connection_name, url, db, username)
            else:
                st.error("Échec de l'authentification. Vérifiez vos identifiants.")
                st.session_state.connection_success = False
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")
            st.session_state.connection_success = False

def extract_data_from_odoo(models_fields):
    """Extrait les données d'Odoo pour les modèles et champs spécifiés."""
    dataframes = {}
    conn_details = st.session_state.conn_details
    models_proxy = st.session_state.models_proxy
    uid = st.session_state.uid

    for model_name, fields in models_fields.items():
        try:
            limit = 5000
            offset = 0
            all_records = []
            while True:
                data_batch = models_proxy.execute_kw(
                    conn_details['db'], uid, conn_details['password'],
                    model_name, 'search_read', [[]],
                    {'fields': fields, 'limit': limit, 'offset': offset}
                )
                if not data_batch:
                    break
                all_records.extend(data_batch)
                offset += limit
                st.info(f"Chargement de {len(all_records)} lignes pour {model_name}...")
            
            # Prétraitement simple des données
            processed_data = []
            for record in all_records:
                new_record = {}
                for field, value in record.items():
                    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
                        new_record[field] = value[0] # Simplifie les champs Many2one
                    elif isinstance(value, (dict, list)):
                        new_record[field] = str(value)
                    else:
                        new_record[field] = value
                processed_data.append(new_record)

            df = pd.DataFrame(processed_data)
            dataframes[model_name] = df
        except Exception as e:
            st.error(f"Erreur lors de l'extraction de {model_name}: {e}")
            return None
    return dataframes