# ai_services.py

import streamlit as st
import openai
import json
import os
import pandas as pd
import kms_services
import xmlrpc.client
import traceback
import logging
import requests

# Importe les templates de prompts (si vous avez créé le fichier prompts.py)
# from prompts import VISUALIZATION_SUGGESTION_PROMPT_TEMPLATE, VISUALIZATION_GUIDE_PROMPT_TEMPLATE

# --- Configuration Hybride de la Clé API ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("La clé API OpenAI n'est pas configurée.")
    st.stop()

# Initialise le client OpenAI une seule fois
client = openai.OpenAI(api_key=OPENAI_API_KEY)


def get_ai_plan(user_prompt, document_text=None):
    """Interroge l'IA en deux étapes pour obtenir le plan de transformation."""
    ai_response_text = None
    try:
        url = st.session_state.conn_details['url']
        logging.info(f"Tentative de connexion réseau brute à l'URL Odoo : {url}")
        try:
            requests.get(url, timeout=10)
        except requests.exceptions.RequestException as net_err:
            logging.error(f"--- ERREUR RÉSEAU DÉTECTÉE ---\n{traceback.format_exc()}")
            st.error(f"Erreur de connexion réseau au serveur Odoo : {net_err}. Le serveur est peut-être inaccessible ou bloqué par un pare-feu.")
            return None
        
        clean_url = url.rstrip('/')
        password_decrypted = kms_services.decrypt_password(st.session_state.conn_details['encrypted_password'])

        with st.spinner("L'IA analyse votre besoin et le schéma Odoo (étape 1/2)..."):
            fresh_models_proxy_s1 = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/object')
            if 'models' not in st.session_state or not st.session_state.models:
                model_data = fresh_models_proxy_s1.execute_kw(
                    st.session_state.conn_details['db'], st.session_state.uid, password_decrypted,
                    'ir.model', 'search_read', [[]], {'fields': ['model']}
                )
                st.session_state.models = sorted([m['model'] for m in model_data if m.get('model')])

            system_message_step1 = "Tu es un expert Odoo. À partir de l'objectif de l'utilisateur et de la liste complète des modèles, réponds UNIQUEMENT avec un objet JSON contenant une seule clé 'relevant_models' qui est une liste de noms de modèles pertinents."
            full_prompt_for_ai = f"Objectif de l'utilisateur: {user_prompt}\n\nContenu du document fourni:\n{document_text or 'Aucun'}"
            
            response_step1 = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message_step1},
                    {"role": "user", "content": f"{full_prompt_for_ai}\n\nModèles disponibles: {st.session_state.models}"}
                ],
                response_format={"type": "json_object"}
            )
            relevant_models = json.loads(response_step1.choices[0].message.content)['relevant_models']

        with st.spinner("L'IA génère le code de transformation (étape 2/2)..."):
            targeted_schema = {}
            fresh_models_proxy_s2 = xmlrpc.client.ServerProxy(f'{clean_url}/xmlrpc/2/object')
            for model_name in relevant_models:
                if model_name in st.session_state.models:
                    try:
                        fields_data = fresh_models_proxy_s2.execute_kw(
                            st.session_state.conn_details['db'], st.session_state.uid, password_decrypted,
                            model_name, 'fields_get', [], {}
                        )
                        targeted_schema[model_name] = sorted(fields_data.keys())
                    except:
                        continue
            
            schema_str = json.dumps(targeted_schema, indent=2)
            
            # --- PROMPT SYSTÈME MIS À JOUR ---
            system_message_step2 = """
            Tu es un expert Odoo et Python/Pandas. Ton rôle est de générer un plan d'extraction et un code de transformation robustes.
            Tu dois répondre UNIQUEMENT avec un bloc de code JSON valide.
            Le JSON doit contenir deux clés : "models_and_fields" et "python_code".

            La valeur de "python_code" DOIT être une chaîne de caractères contenant une unique fonction Python nommée `transform_data` qui prend un seul argument : `dfs`.
            Cet argument `dfs` est un dictionnaire où les clés sont les noms des modèles et les valeurs sont les DataFrames Pandas bruts correspondants.
            La fonction DOIT retourner un unique DataFrame Pandas.

            TACHES DE NETTOYAGE OBLIGATOIRES : Au début de ta fonction `transform_data`, tu DOIS effectuer les opérations de nettoyage suivantes sur chaque DataFrame reçu dans `dfs`:
            1. Pour toute colonne contenant 'date' dans son nom, tu dois la convertir en datetime UTC de manière robuste. Utilise `pd.to_datetime(df[col], errors='coerce')` puis gère la localisation en UTC.
            2. Pour les colonnes numériques, convertis-les avec `pd.to_numeric(df[col], errors='coerce')`.

            ---
            RÈGLE FONDAMENTALE SUR L'ACCÈS AUX DONNÉES :
            Tu ne dois JAMAIS tenter d'accéder à des champs de modèles liés qui n'ont pas été explicitement listés dans le schéma fourni. Ton code doit fonctionner **uniquement** avec les colonnes présentes dans les dataframes du dictionnaire `dfs`.
            - **Exemple de ce qu'il ne faut PAS faire :** Pour un DataFrame `account_move_line_df`, le code NE DOIT PAS faire `df['move_id']['state']` ou chercher un champ inventé comme `parent_state`. CELA PROVOQUERA UNE ERREUR.
            - **Exemple de ce qu'il FAUT faire :** Si tu as besoin de l'état de la facture, ton plan d'extraction initial (`models_and_fields`) DOIT inclure le modèle `account.move` avec le champ `state`. Ensuite, dans ton code Python, tu DOIS effectuer une jointure explicite : `pd.merge(account_move_line_df, account_move_df, left_on='move_id', right_on='id')`.
            ---

            RÈGLE CRUCIALE SUR LES DATES : Pour toute comparaison ou création de date, utilise OBLIGATOIREMENT `pd.Timestamp` avec un fuseau horaire UTC (`tz='UTC'`).

            RÈGLE CRUCIALE SUR LE CODE PANDAS : N'utilise JAMAIS `DataFrame.append()`. Utilise OBLIGATOIREMENT `pd.concat()`.
            """
            
            final_user_prompt = f"{full_prompt_for_ai}\n\nSchéma des modèles pertinents:\n{schema_str}"
            st.session_state.conversation_history = [{"role": "system", "content": system_message_step2}, {"role": "user", "content": final_user_prompt}]
            
            response_step2 = client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.conversation_history,
                response_format={"type": "json_object"}
            )
            ai_response_text = response_step2.choices[0].message.content
            return json.loads(ai_response_text)

    except xmlrpc.client.ProtocolError as p_err:
        st.error(f"Erreur de protocole Odoo ({p_err.errcode}): {p_err.errmsg}")
        logging.error(f"--- ODOO PROTOCOL ERROR in get_ai_plan ---\n{traceback.format_exc()}")
        return None
    except Exception as e:
        st.error(f"Erreur lors de la génération du plan par l'IA : {e}")
        logging.error(f"--- GENERIC ERROR in get_ai_plan ---\n{traceback.format_exc()}")
        if ai_response_text:
            st.code(ai_response_text, language='text')
        return None


def run_ai_code(ai_python_code, dataframes):
    """Exécute le code python généré par l'IA."""
    exec_scope = {'pd': pd, 'dfs': dataframes}
    try:
        exec(ai_python_code, exec_scope)
        if 'transform_data' not in exec_scope:
            st.error("Erreur critique de l'IA : La fonction 'transform_data' est manquante.")
            st.code(ai_python_code, language='python')
            return None
            
        transform_function = exec_scope['transform_data']
        result_df = transform_function(dataframes)
        return result_df
    except Exception as e:
        st.error(f"Le code de l'IA a échoué lors de son exécution : {e}")
        st.code(ai_python_code, language='python')
        return None

# ==============================================================================
# ▼▼▼ FONCTIONS POUR L'ASSISTANT DE VISUALISATION ▼▼▼
# ==============================================================================

def get_ai_visualization_suggestion(user_prompt: str) -> dict:
    """
    Interroge l'IA pour obtenir une suggestion de visualisation (outil, type de graphique).
    NOTE: Cette fonction n'est plus utilisée dans le flux actuel mais est conservée au cas où.
    """
    try:
        # Prompt à définir dans prompts.py si nécessaire
        prompt = f"Basé sur cet objectif: '{user_prompt}', suggère le meilleur outil de BI et type de graphique en JSON."
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Tu es un expert en Business Intelligence. Réponds en JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        suggestion = json.loads(response.choices[0].message.content)
        return suggestion
    except Exception as e:
        st.error(f"Erreur lors de la génération de la suggestion de visualisation : {e}")
        logging.error(f"--- ERROR in get_ai_visualization_suggestion ---\n{traceback.format_exc()}")
        return {"recommendation_text": "Désolé, une erreur est survenue lors de la suggestion."}

def get_ai_visualization_guide(context: dict) -> str:
    """
    Interroge l'IA pour générer un guide de visualisation pas à pas.
    """
    try:
        # NOTE: Le prompt est maintenant dans prompts.py. S'il n'est pas importé, il faut le définir ici.
        from prompts import VISUALIZATION_GUIDE_PROMPT_TEMPLATE

        prompt = VISUALIZATION_GUIDE_PROMPT_TEMPLATE.format(
            user_goal=context.get("user_goal"),
            tool=context.get("tool"),
            chart_type=context.get("chart_type"),
            project_id=context.get("project_id"),
            dataset_id=context.get("dataset_id"),
            view_name=context.get("view_name"),
            columns=context.get("columns")
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Tu es un formateur expert en Business Intelligence."},
                {"role": "user", "content": prompt}
            ]
        )
        guide = response.choices[0].message.content
        return guide
    except Exception as e:
        st.error(f"Erreur lors de la génération du guide de visualisation : {e}")
        logging.error(f"--- ERROR in get_ai_visualization_guide ---\n{traceback.format_exc()}")
        return "Désolé, une erreur est survenue lors de la génération du guide."