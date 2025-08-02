import streamlit as st
import xmlrpc.client
import pandas as pd
from database import save_connection
import kms_services

def attempt_connection():
    """
    Tente de se connecter à Odoo.
    Utilise la clé sauvegardée si elle existe, sinon utilise le mot de passe du formulaire.
    """
    url = st.session_state.url_input
    db = st.session_state.db_input
    username = st.session_state.username_input
    
    password_from_form = st.session_state.password_input
    saved_conn_details = st.session_state.get('conn_details', {})

    if not all([url, db, username]):
        st.error("L'URL, la base de données et l'utilisateur sont requis.")
        return

    password_to_use = None
    encrypted_pass_to_save = None

    # Scénario 1: Utiliser une connexion sauvegardée (le champ mdp est vide mais on a une clé chiffrée en session)
    if not password_from_form and saved_conn_details.get('encrypted_password'):
        try:
            encrypted_pass_to_save = saved_conn_details['encrypted_password']
            password_to_use = kms_services.decrypt_password(encrypted_pass_to_save)
        except Exception as e:
            st.error(f"Erreur lors du déchiffrement de la clé API sauvegardée : {e}")
            return
            
    # Scénario 2: Nouvelle connexion ou modification du mot de passe (le champ mdp est rempli)
    elif password_from_form:
        password_to_use = password_from_form
        try:
            encrypted_pass_to_save = kms_services.encrypt_password(password_to_use)
        except Exception as e:
            st.error(f"Erreur lors du chiffrement de la nouvelle clé API : {e}")
            return
    
    # Scénario 3: Erreur, aucun mot de passe fourni
    else:
        st.error("Veuillez entrer un mot de passe pour une nouvelle connexion.")
        return

    # --- Tentative de connexion à Odoo ---
    with st.spinner("Connexion à Odoo..."):
        try:
            clean_url = url.rstrip('/')
            common = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/common')
            uid = common.authenticate(db, username, password_to_use, {})

            if uid:
                models_proxy = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/object')
                
                st.session_state.models_proxy = models_proxy
                st.session_state.uid = uid
                st.session_state.conn_details = {
                    'url': url, 'db': db, 'username': username, 
                    'encrypted_password': encrypted_pass_to_save
                }
                st.session_state.connection_success = True

                connection_name = f"{db} ({username})"
                save_connection(
                    name=connection_name, url=url, db_name=db, 
                    username=username, encrypted_password=encrypted_pass_to_save
                )
            else:
                st.error("Échec de l'authentification. Vérifiez vos identifiants.")
                st.session_state.connection_success = False
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")
            st.session_state.connection_success = False


def extract_data_from_odoo(models_fields):
    """
    Extrait les données d'Odoo pour les modèles et champs spécifiés.
    Cette fonction est inchangée mais incluse pour que le fichier soit complet.
    """
    dataframes = {}
    conn_details = st.session_state.conn_details
    models_proxy = st.session_state.models_proxy
    uid = st.session_state.uid

    try:
        encrypted_pass_from_session = conn_details['encrypted_password']
        odoo_password = kms_services.decrypt_password(encrypted_pass_from_session)
    except Exception as e:
        st.error(f"Impossible de déchiffrer la clé API Odoo. Erreur: {e}")
        return None

    for model_name, fields in models_fields.items():
        try:
            limit = 5000
            offset = 0
            all_records = []
            while True:
                data_batch = models_proxy.execute_kw(
                    conn_details['db'], uid, odoo_password,
                    model_name, 'search_read', [[]],
                    {'fields': fields, 'limit': limit, 'offset': offset}
                )
                if not data_batch:
                    break
                all_records.extend(data_batch)
                offset += limit
                st.info(f"Chargement de {len(all_records)} lignes pour {model_name}...")
            
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
        except Exception as e:
            st.error(f"Erreur lors de l'extraction de {model_name}: {e}")
            return None
    return dataframes