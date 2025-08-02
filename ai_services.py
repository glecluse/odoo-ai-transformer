import streamlit as st
import openai
import json
import os
import pandas as pd # <-- Ajout de l'import pour la fonction run_ai_code

# --- Configuration Hybride de la Clé API ---
# Cherche d'abord dans les variables d'environnement (pour Cloud Run)
# Sinon, cherche dans les secrets de Streamlit (pour le local)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

# Vérification pour s'assurer que la clé est bien configurée
if not OPENAI_API_KEY:
    # Cette erreur s'affichera dans l'interface Streamlit si la clé n'est pas trouvée
    st.error("La clé API OpenAI n'est pas configurée. Vérifiez vos variables d'environnement ou le fichier secrets.toml.")
    # st.stop() arrête l'exécution du script pour éviter d'autres erreurs.
    st.stop()


def get_ai_plan(user_prompt, document_text):
    """Interroge l'IA en deux étapes pour obtenir le plan de transformation."""
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    ai_response_text = None # Initialisation pour le bloc try/except

    try:
        # --- Étape 1: Obtenir les modèles pertinents ---
        with st.spinner("L'IA analyse votre besoin et le schéma Odoo (étape 1/2)..."):
            if 'models' not in st.session_state or not st.session_state.models:
                model_data = st.session_state.models_proxy.execute_kw(
                    st.session_state.conn_details['db'], st.session_state.uid, st.session_state.conn_details['password'],
                    'ir.model', 'search_read', [[]], {'fields': ['model']}
                )
                st.session_state.models = sorted([m['model'] for m in model_data if m.get('model')])

            system_message_step1 = "Tu es un expert Odoo. À partir de l'objectif de l'utilisateur et de la liste complète des modèles, réponds UNIQUEMENT avec un objet JSON contenant une seule clé 'relevant_models' qui est une liste de noms de modèles pertinents."
            full_prompt_for_ai = f"Objectif de l'utilisateur: {user_prompt}\n\nContenu du document fourni:\n{document_text}"
            
            response_step1 = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message_step1},
                    {"role": "user", "content": f"{full_prompt_for_ai}\n\nModèles disponibles: {st.session_state.models}"}
                ],
                response_format={"type": "json_object"}
            )
            relevant_models = json.loads(response_step1.choices[0].message.content)['relevant_models']

        # --- Étape 2: Obtenir les champs et le code de transformation ---
        with st.spinner("L'IA génère le code de transformation (étape 2/2)..."):
            targeted_schema = {}
            for model_name in relevant_models:
                if model_name in st.session_state.models:
                    try:
                        password_decrypted = kms_services.decrypt_password(st.session_state.conn_details['encrypted_password'])
                        fields_data = st.session_state.models_proxy.execute_kw(
                            st.session_state.conn_details['db'], st.session_state.uid, password_decrypted,
                            model_name, 'fields_get', [], {}
                        )
                        targeted_schema[model_name] = sorted(fields_data.keys())
                    except:
                        continue
            
            schema_str = json.dumps(targeted_schema, indent=2)
            system_message_step2 = """
            Tu es un expert Odoo et Python/Pandas. Ton rôle est de générer un plan d'extraction et un code de transformation robustes.
            Tu dois répondre UNIQUEMENT avec un bloc de code JSON valide.
            Le JSON doit contenir deux clés : "models_and_fields" et "python_code".
            La valeur de "python_code" DOIT être une chaîne de caractères contenant une unique fonction Python nommée `transform_data` qui prend un seul argument : `dfs`.
            Cet argument `dfs` est un dictionnaire où les clés sont les noms des modèles et les valeurs sont les DataFrames Pandas bruts correspondants.
            La fonction DOIT retourner un unique DataFrame Pandas.

            TACHES DE NETTOYAGE OBLIGATOIRES : Au début de ta fonction `transform_data`, tu DOIS effectuer les opérations de nettoyage suivantes sur chaque DataFrame reçu dans `dfs`:
            1.  Pour toute colonne contenant 'date' dans son nom, convertis-la en datetime UTC avec `df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize('UTC')`.
            2.  Pour les colonnes numériques typiques ('price', 'qty', 'amount', 'id', 'partner_id', etc.), convertis-les avec `pd.to_numeric(df[col], errors='coerce')`.
            Seulement après ce nettoyage, applique la logique métier demandée.

            RÈGLE CRUCIALE SUR LES DATES : Pour toute comparaison ou création de date, utilise OBLIGATOIREMENT `pd.Timestamp` avec un fuseau horaire UTC. N'utilise JAMAIS `datetime.datetime`. Par exemple, pour le 1er janvier 2025, le code doit utiliser `pd.Timestamp('2025-01-01', tz='UTC')`.
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

    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'IA : {e}")
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