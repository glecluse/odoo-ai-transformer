# odoo.py

import streamlit as st
import xmlrpc.client
import pandas as pd
from database import save_connection
import kms_services
import traceback

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

    if not password_from_form and saved_conn_details.get('encrypted_password'):
        try:
            encrypted_pass_to_save = saved_conn_details['encrypted_password']
            password_to_use = kms_services.decrypt_password(encrypted_pass_to_save)
        except Exception as e:
            st.error(f"Erreur lors du déchiffrement de la clé API sauvegardée : {e}")
            return
            
    elif password_from_form:
        password_to_use = password_from_form
        try:
            encrypted_pass_to_save = kms_services.encrypt_password(password_to_use)
        except Exception as e:
            st.error(f"Erreur lors du chiffrement de la nouvelle clé API : {e}")
            return
    
    else:
        st.error("Veuillez entrer un mot de passe pour une nouvelle connexion.")
        return

    with st.spinner("Connexion à Odoo..."):
        try:
            clean_url = url.rstrip('/')
            common = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/common')
            uid = common.authenticate(db, username, password_to_use, {})

            if uid:
                models_proxy = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/object')
                
                # 1. On crée le nom de la connexion d'abord
                connection_name = f"{db} ({username})"
                
                # 2. On stocke TOUTES les informations dans la session, y compris le nom
                st.session_state.models_proxy = models_proxy
                st.session_state.uid = uid
                st.session_state.password_to_use = password_to_use
                st.session_state.conn_details = {
                    'name': connection_name, # <-- LIGNE CORRIGÉE
                    'url': url, 
                    'db': db, 
                    'username': username, 
                    'encrypted_password': encrypted_pass_to_save
                }
                st.session_state.connection_success = True

                # 3. On sauvegarde en base de données
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

def get_large_dataset_paginated(models_proxy, db, uid, password, model_name, domain=[], fields=[], chunk_size=2000):
    """
    Récupère un grand volume de données d'Odoo par lots (pagination).
    C'est un générateur qui "yield" des DataFrames Pandas pour chaque lot.
    """
    offset = 0
    print(f"Début de la récupération paginée pour le modèle {model_name}...")
    
    while True:
        try:
            print(f"Récupération du lot : offset={offset}, limit={chunk_size}")
            
            records = models_proxy.execute_kw(
                db, uid, password, model_name, 'search_read',
                [domain],
                {'fields': fields, 'limit': chunk_size, 'offset': offset}
            )

            if not records:
                print("Fin de la récupération : plus de données.")
                break

            processed_data = []
            for record in records:
                new_record = {}
                for field, value in record.items():
                    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
                        new_record[field] = value[0]
                    elif isinstance(value, (dict, list)):
                        new_record[field] = str(value)
                    else:
                        new_record[field] = value
                processed_data.append(new_record)

            yield pd.DataFrame(processed_data)

            offset += chunk_size

        except Exception as e:
            print(f"Une erreur est survenue lors de la récupération du lot à l'offset {offset}: {e}")
            raise e