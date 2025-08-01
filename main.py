import streamlit as st
import xmlrpc.client
import pandas as pd
from io import StringIO
import datetime
import openai
import json
import re
import PyPDF2
import sqlite3
import inspect

# --- CONFIGURATION DE L'APPLICATION ---
from cryptography.fernet import Fernet

SAVED_PASSWORD_PLACEHOLDER = "••••••••••"
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
FERNET_KEY = st.secrets.get("FERNET_KEY")

st.set_page_config(layout="wide", page_title="Odoo AI Transformer", page_icon="🤖")

# --- FONCTIONS UTILITAIRES ---

def sanitize_for_gcs(text: str) -> str:
    """Nettoie une chaîne de caractères pour la rendre compatible avec les noms de GCS."""
    if not text:
        return "export-odoo"
    text = text.lower()
    text = text.replace(' ', '-')
    text = re.sub(r'[^\w-]', '', text) # Garde les caractères alphanumériques et les tirets
    text = re.sub(r'--+', '-', text)   # Remplace les tirets multiples par un seul
    text = text.strip('-')
    return text or "export-odoo" # Retourne un nom par défaut si la chaîne est vide

def generate_and_display_key():
    key = Fernet.generate_key().decode()
    st.warning("⚠️ Clé de chiffrement non trouvée !")
    st.info("Veuillez ajouter la ligne suivante à votre fichier `.streamlit/secrets.toml` :")
    st.code(f'FERNET_KEY = "{key}"')
    return None

if FERNET_KEY:
    FERNET = Fernet(FERNET_KEY.encode())
else:
    FERNET = None

def encrypt_data(data: str) -> bytes:
    if not FERNET: return None
    return FERNET.encrypt(data.encode())

def decrypt_data(encrypted_data: bytes) -> str:
    if not FERNET or not encrypted_data: return None
    try:
        return FERNET.decrypt(encrypted_data).decode()
    except Exception:
        return None

# --- GESTION DE LA BASE DE DONNÉES LOCALE ---
DB_FILE = "connections.db"

def init_db():
    with sqlite3.connect(DB_FILE) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, url TEXT NOT NULL,
                db_name TEXT NOT NULL, username TEXT NOT NULL, password_encrypted BLOB
            )""")
        con.commit()

def load_connections():
    with sqlite3.connect(DB_FILE) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM connections ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

def save_connection(name, url, db_name, username, password):
    if not FERNET: return
    encrypted_password = encrypt_data(password)
    with sqlite3.connect(DB_FILE) as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO connections (name, url, db_name, username, password_encrypted) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                url=excluded.url, db_name=excluded.db_name, username=excluded.username,
                password_encrypted=excluded.password_encrypted
        """, (name, url, db_name, username, encrypted_password))
        con.commit()

# --- LOGIQUE MÉTIER ET IA ---
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

def generate_looker_studio_instructions(user_prompt, df_schema, bq_view_name):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    system_message = f"""
Tu es un expert en Business Intelligence et un consultant Looker Studio. Ta mission est de rédiger un guide étape par étape pour un utilisateur afin qu'il puisse construire une visualisation pertinente.

CONTEXTE :
- L'utilisateur vient de créer une vue BigQuery nommée `{bq_view_name}`.
- Le schéma de cette vue est le suivant : `{df_schema}`.
- L'objectif initial de l'utilisateur était : "{user_prompt}".

TA MISSION :
1.  **Analyse et suggère :** En te basant sur l'objectif et le schéma, identifie les dimensions (texte, date) et les métriques (nombres).
2.  **Recommandation Principale :** Propose le type de graphique le plus adapté à la demande principale de l'utilisateur (Graphique temporel, Barres, Tableau, etc.).
3.  **Recommandation Alternative :** Propose une seconde visualisation pertinente qui pourrait apporter un éclairage différent ou plus profond (Carte de densité, Nuage de points, Scorecard avec KPIs, etc.).
4.  **Rédige les Instructions :** Pour CHAQUE recommandation, fournis un guide détaillé et numéroté en Markdown. Sois très clair et simple. Les instructions doivent inclure :
    a.  La connexion à la source de données BigQuery.
    b.  L'ajout du type de graphique recommandé.
    c.  La configuration précise des champs : quel champ glisser dans "Dimension", "Dimension de répartition", "Métrique", "Période".
    d.  Quelques conseils de style ou de tri pour améliorer la lisibilité.

FORMAT :
- Réponds en FRANÇAIS.
- Utilise des titres Markdown (`##`), des listes numérotées et du texte en gras.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_message}]
    )
    return response.choices[0].message.content

def generate_gcp_function_code(url, db, username, project_id, file_name_prefix, model_fields_dict, ai_python_code):
    clean_url = url.rstrip('/')
    secret_name = f"api_key_{db.replace('-', '_')}"
    bucket_name = db.replace('_', '-')
    extraction_function_code = inspect.getsource(extract_and_process_odoo_data)
    models_to_export_str = json.dumps(model_fields_dict, indent=4)

    code = f"""# Fichier: main.py - Prêt pour déploiement sur Google Cloud Functions
import xmlrpc.client
import os
import datetime
import pandas as pd
import re
import json
from google.cloud import storage, secretmanager
from io import StringIO

# ==================================================================
# === DÉBUT DU CODE DE TRANSFORMATION GÉNÉRÉ PAR L'IA ===
# ==================================================================
{ai_python_code}
# ==================================================================
# === FIN DU CODE DE TRANSFORMATION GÉNÉRÉ PAR L'IA ===
# ==================================================================

# ==================================================================
# === DÉBUT DE LA LOGIQUE D'EXTRACTION CENTRALISÉE ===
# ==================================================================
def st_empty_mock():
    class MockEmpty:
        def info(self, msg): print(msg)
        def empty(self): pass
    return MockEmpty()

{extraction_function_code.replace("st.empty()", "st_empty_mock()")}
# ==================================================================
# === FIN DE LA LOGIQUE D'EXTRACTION CENTRALISÉE ===
# ==================================================================

# Le "Point d'entrée" à renseigner dans la console GCP
def odoo_etl_to_gcs(request):
    try:
        ODOO_URL = "{clean_url}"
        ODOO_DB = "{db}"
        ODOO_USER = "{username}"
        PROJECT_ID = "{project_id}"
        SECRET_NAME = "{secret_name}"
        SECRET_VERSION_NAME = f"projects/{{PROJECT_ID}}/secrets/{{SECRET_NAME}}/versions/latest"
        secret_client = secretmanager.SecretManagerServiceClient()
        response = secret_client.access_secret_version(name=SECRET_VERSION_NAME)
        ODOO_PASSWORD = response.payload.data.decode("UTF-8")
        common = xmlrpc.client.ServerProxy(f'{{ODOO_URL}}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {{}})
        models_proxy = xmlrpc.client.ServerProxy(f'{{ODOO_URL}}/xmlrpc/2/object')
        conn_details = {{'db': ODOO_DB, 'uid': uid, 'password': ODOO_PASSWORD}}
    except Exception as e:
        print(f"ERREUR CRITIQUE (Connexion): {{e}}")
        return (f"ERREUR CRITIQUE (Connexion): {{e}}", 500)

    MODELS_TO_EXTRACT = {models_to_export_str}
    try:
        dfs = extract_and_process_odoo_data(models_proxy, conn_details, MODELS_TO_EXTRACT)
    except Exception as e:
        print(f"ERREUR CRITIQUE (Extraction): {{e}}")
        return (f"ERREUR CRITIQUE (Extraction): {{e}}", 500)

    try:
        result_df = transform_data(dfs)
    except Exception as e:
        print(f"ERREUR CRITIQUE (Transformation IA): {{e}}")
        return (f"ERREUR CRITIQUE (Transformation IA): {{e}}", 500)

    cleaned_columns = [re.sub(r'[^a-zA-Z0-9_]+', '_', str(col)).strip('_') for col in result_df.columns]
    result_df.columns = ['_' + col if col and col[0].isdigit() else col for col in cleaned_columns]
    
    try:
        GCS_BUCKET_NAME = "{bucket_name}"
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        if not bucket.exists():
            storage_client.create_bucket(bucket, location="europe-west1")
        json_buffer = StringIO()
        result_df.to_json(json_buffer, orient='records', lines=True, date_format='iso')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"{file_name_prefix}_{{timestamp}}.jsonl"
        bucket.blob(file_name).upload_from_string(json_buffer.getvalue(), content_type='application/jsonl')
        print(f"Fichier {{file_name}} chargé avec succès dans le bucket {{GCS_BUCKET_NAME}}.")
    except Exception as e:
        print(f"ERREUR CRITIQUE (Chargement GCS): {{e}}")
        return (f"ERREUR CRITIQUE (Chargement GCS): {{e}}", 500)
    
    return ("ETL complet terminé avec succès.", 200)
"""
    return code

def generate_bigquery_view_code(project_id, dataset_id, view_name, file_name_prefix):
    final_table_name = file_name_prefix
    return f"""CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.{view_name}` AS (SELECT * FROM `{project_id}.{dataset_id}.{final_table_name}`);"""


def attempt_connection():
    url, db, username, password = st.session_state.url_input, st.session_state.db_input, st.session_state.username_input, st.session_state.password_input
    if password == SAVED_PASSWORD_PLACEHOLDER: password = ""
    if not password:
        selected_name = st.session_state.get('connection_selector')
        if selected_name and selected_name != "Nouvelle connexion...":
            connections = load_connections()
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
                save_connection(connection_name, url, db, username, password)
                st.success(f"Connexion '{connection_name}' réussie et sauvegardée.")
            else:
                st.error("Échec de l'authentification."); st.session_state.connection_success = False
        except Exception as e:
            st.error(f"Erreur de connexion : {e}"); st.session_state.connection_success = False


# --- INTERFACE UTILISATEUR (UI) ---
init_db()
st.title("🤖 Odoo AI Data Transformer")

if not OPENAI_API_KEY:
    st.error("La clé API OpenAI n'est pas configurée.")
    st.stop()
if not FERNET:
    generate_and_display_key()
    st.stop()

for key in ['connection_success', 'models', 'ai_models_fields', 'ai_python_code', 'transformed_df', 'assembled_user_prompt', 'default_gcp_name']:
    if key not in st.session_state:
        st.session_state[key] = None

with st.sidebar:
    st.header("🔌 Connexion Odoo")
    connections = load_connections()
    connection_names = ["Nouvelle connexion..."] + [c['name'] for c in connections]
    if 'selected_connection' not in st.session_state: st.session_state.selected_connection = connection_names[0]
    def on_connection_change():
        selected_name = st.session_state.connection_selector
        if selected_name != "Nouvelle connexion...":
            connections_list = load_connections()
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
    st.button("Se connecter / Mettre à jour", on_click=attempt_connection)

if not st.session_state.get('connection_success'):
    st.info("👋 Bienvenue ! Connectez-vous à votre instance Odoo pour commencer.")
else:
    st.header("1. Décrire l'objectif de la transformation")
    st.info("Guidez l'IA en structurant votre demande. Plus vous serez précis, meilleur sera le résultat.")
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
            st.warning("Veuillez remplir au moins une partie du formulaire ou télécharger un document.")
        else:
            with st.spinner("L'IA analyse votre besoin et le schéma (étape 1/2)..."):
                document_text = ""
                if uploaded_file is not None:
                    try:
                        if uploaded_file.type == "application/pdf":
                            pdf_reader = PyPDF2.PdfReader(uploaded_file)
                            document_text = "".join(page.extract_text() for page in pdf_reader.pages)
                        elif uploaded_file.type == "text/plain":
                            document_text = uploaded_file.getvalue().decode("utf-8")
                    except Exception as e:
                        st.error(f"Erreur lors de la lecture du fichier : {e}"); st.stop()
                full_prompt_for_ai = f"Objectif de l'utilisateur:\n{user_prompt}\n\nContenu du document fourni:\n{document_text}"
                ai_response_text = None
                try:
                    client = openai.OpenAI(api_key=OPENAI_API_KEY)
                    if 'models' not in st.session_state or not st.session_state.get('models'):
                        model_data = st.session_state.models_proxy.execute_kw(st.session_state.conn_details['db'], st.session_state.uid, st.session_state.conn_details['password'], 'ir.model', 'search_read', [[]], {'fields': ['model']})
                        st.session_state.models = sorted([m['model'] for m in model_data if m.get('model')])
                    system_message_step1 = "Tu es un expert Odoo. À partir de l'objectif de l'utilisateur et de la liste complète des modèles, réponds UNIQUEMENT avec un objet JSON contenant une seule clé 'relevant_models' qui est une liste de noms de modèles pertinents."
                    response_step1 = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_message_step1}, {"role": "user", "content": f"{full_prompt_for_ai}\n\nModèles disponibles: {st.session_state.models}"}], response_format={"type": "json_object"})
                    relevant_models = json.loads(response_step1.choices[0].message.content)['relevant_models']
                    st.spinner("L'IA génère le code de transformation (étape 2/2)...")
                    targeted_schema = {}
                    for model_name in relevant_models:
                        if model_name in st.session_state.models:
                            try:
                                fields_data = st.session_state.models_proxy.execute_kw(st.session_state.conn_details['db'], st.session_state.uid, st.session_state.conn_details['password'], model_name, 'fields_get', [], {})
                                targeted_schema[model_name] = sorted(fields_data.keys())
                            except: continue
                    schema_str = json.dumps(targeted_schema, indent=2)
                    system_message_step2 = """Tu es un expert Odoo et Python/Pandas. Ton rôle est de générer un plan d'extraction et un code de transformation robustes. Tu dois répondre UNIQUEMENT avec un bloc de code JSON valide. Le JSON doit contenir deux clés : "models_and_fields" et "python_code". La valeur de "python_code" DOIT être une chaîne de caractères contenant une unique fonction Python nommée `transform_data` qui prend un seul argument : `dfs`. Cet argument `dfs` est un dictionnaire où les clés sont les noms des modèles et les valeurs sont les DataFrames Pandas bruts correspondants. La fonction DOIT retourner un unique DataFrame Pandas.

TACHES DE NETTOYAGE OBLIGATOIRES : Au début de ta fonction `transform_data`, tu DOIS effectuer les opérations de nettoyage suivantes sur chaque DataFrame reçu dans `dfs`:
1.  Pour toute colonne contenant 'date' dans son nom, convertis-la en datetime UTC avec `df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize('UTC')`.
2.  Pour les colonnes numériques typiques ('price', 'qty', 'amount', 'id', 'partner_id', etc.), convertis-les avec `pd.to_numeric(df[col], errors='coerce')`.
3.  Prévention des erreurs de type : Si tu crées une colonne de période (ex: `df['mois'] = df['date'].dt.to_period('M')`), ne tente JAMAIS d'appliquer une autre transformation `.dt` sur cette même colonne `df['mois']`. Les transformations de date/période doivent toujours partir de la colonne `datetime` originale.

Seulement après ce nettoyage, applique la logique métier demandée.

RÈGLES OPÉRATIONNELLES CRUCIALES :
- GESTION DES DATES :
  - Création : Pour toute comparaison ou création de date, utilise OBLIGATOIREMENT `pd.Timestamp` avec un fuseau horaire UTC. Ex: `pd.Timestamp('2025-01-01', tz='UTC')`.
  - Comparaisons : Toute comparaison de date doit se faire entre objets de même nature.
    CORRECT : `df['date_commande'] > pd.Timestamp('2025-01-01', tz='UTC')`
    INCORRECT : `df['date_commande'] > pd.Timestamp('2025-01-01')` (provoque une erreur).
- SÉCURITÉ DES FUSIONS (MERGE) : Après avoir fusionné des dataframes, le nombre de lignes change. N'assigne JAMAIS une colonne d'un dataframe à un autre s'ils n'ont pas le même index. Crée toujours les nouvelles colonnes sur le dataframe final issu de la fusion.
"""
                    final_user_prompt = f"{full_prompt_for_ai}\n\nSchéma des modèles pertinents:\n{schema_str}"
                    response_step2 = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_message_step2}, {"role": "user", "content": final_user_prompt}], response_format={"type": "json_object"})
                    ai_response_text = response_step2.choices[0].message.content
                    if ai_response_text:
                        ai_response_json = json.loads(ai_response_text)
                        st.session_state.ai_models_fields = ai_response_json['models_and_fields']
                        st.session_state.ai_python_code = ai_response_json['python_code']
                        st.session_state.transformed_df = None
                    else:
                        st.error("L'IA a renvoyé une réponse vide.")
                except Exception as e:
                    st.error(f"Erreur lors de l'appel à l'IA : {e}")
                    if ai_response_text: st.code(ai_response_text, language='text')

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
            project_id = st.text_input("ID du projet GCP", value="lpde-dashboards", key="gcp_project_id")
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
2.  **Ouvrez un terminal** à l'emplacement de ces fichiers.
3.  **Exécutez la commande `gcloud` suivante :**
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
4.  **Important :** Assurez-vous que le compte de service de votre fonction a bien le rôle **"Accesseur de secrets Secret Manager"**.
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