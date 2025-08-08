# gcp.py

import re
import datetime
from io import StringIO

def generate_gcp_function_code(url, db, username, file_name_prefix, model_fields_dict, ai_python_code, license_key):
    clean_url = url.rstrip('/')
    secret_name = f"api_key_{db.replace('-', '_')}"
    bucket_name = db.replace('_', '-')
    
    # URL de votre API de licence
    license_server_url = "https://europe-west1-odoo-ai-transformer.cloudfunctions.net/license-api-handler"

    models_to_export_str = "{\n"
    for model, fields in model_fields_dict.items():
        fields_str = ", ".join([f"'{f}'" for f in fields])
        models_to_export_str += f"        '{model}': [{fields_str}],\n"
    models_to_export_str += "    }"
    
    code = f"""# --- Google Cloud Function pour un ETL Odoo dynamique avec IA ---
import xmlrpc.client, os, datetime, pandas as pd, re, requests, traceback
from google.cloud import storage, secretmanager
import google.auth
from io import StringIO

# --- Bloc de vérification de licence ---
LICENSE_KEY = "{license_key}"
LICENSE_SERVER_URL = "{license_server_url}"

def check_license():
    \"\"\"Appelle le serveur de licence pour vérifier le statut de l'abonnement.\"\"\"
    print(f"--- Début de la vérification de licence ---")
    print(f"Appel de l'URL du serveur de licence : {{LICENSE_SERVER_URL}}")
    try:
        response = requests.post(LICENSE_SERVER_URL, json={{'license_key': LICENSE_KEY}}, timeout=20)
        print(f"Réponse du serveur de licence reçue avec le statut : {{response.status_code}}")
        if response.status_code == 200:
            data = response.json()
            print(f"Données de la réponse : {{data}}")
            if data.get("status") == "active":
                print("Licence active. Démarrage du job.")
                return True
            else:
                print(f"Licence inactive : {{data.get('message')}}")
                return False
        else:
            print(f"Erreur de communication avec le serveur de licence. Contenu de la réponse : {{response.text}}")
            return False
    except requests.exceptions.RequestException as e:
        print("--- ERREUR CRITIQUE LORS DE L'APPEL AU SERVEUR DE LICENCE ---")
        print(f"Une erreur de réseau ou de connexion a empêché de joindre le serveur.")
        print(f"Détail de l'erreur : {{e}}")
        print(traceback.format_exc())
        print("---------------------------------------------------------")
        return False

# --- Code de transformation généré par l'IA ---
{ai_python_code}

# --- Fonction principale de l'ETL ---
def odoo_etl_to_gcs(request):
    if not check_license():
        return "Licence invalide ou abonnement expiré.", 403

    try:
        # Découverte automatique du projet via la bibliothèque d'authentification
        try:
            _, PROJECT_ID = google.auth.default()
        except google.auth.exceptions.DefaultCredentialsError:
            return ("ERREUR CRITIQUE: Impossible de déterminer le projet GCP.", 500)

        if not PROJECT_ID:
            raise Exception("La découverte automatique n'a pas pu trouver l'ID du projet.")

        ODOO_URL = "{clean_url}"
        ODOO_DB = "{db}"
        ODOO_USER = "{username}"
        SECRET_NAME = "{secret_name}"
        SECRET_VERSION_NAME = f"projects/{{PROJECT_ID}}/secrets/{{SECRET_NAME}}/versions/latest"
        
        secret_client = secretmanager.SecretManagerServiceClient()
        response = secret_client.access_secret_version(name=SECRET_VERSION_NAME)
        ODOO_PASSWORD = response.payload.data.decode("UTF-8")
        
        common = xmlrpc.client.ServerProxy(f'{{ODOO_URL}}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {{}})
        models = xmlrpc.client.ServerProxy(f'{{ODOO_URL}}/xmlrpc/2/object')
    except Exception as e:
        return (f"ERREUR CRITIQUE (Connexion): {{e}}", 500)

    MODELS_TO_EXTRACT = {models_to_export_str}
    dfs = {{}}
    for model_name, fields in MODELS_TO_EXTRACT.items():
        try:
            limit = 5000; offset = 0; all_data = []
            while True:
                data_batch = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model_name, 'search_read', [[]], {{'fields': fields, 'limit': limit, 'offset': offset}})
                if not data_batch: break
                all_data.extend(data_batch)
                offset += limit
            
            processed_data = []
            for record in all_data:
                new_record = {{}}
                for field, value in record.items():
                    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int): new_record[field] = value[0]
                    elif isinstance(value, (dict, list)): new_record[field] = str(value)
                    else: new_record[field] = value
                processed_data.append(new_record)
            df = pd.DataFrame(processed_data)
            dfs[model_name] = df
        except Exception as e:
            return (f"Erreur lors du chargement du modèle {{model_name}}: {{e}}", 500)
            
    try:
        result_df = transform_data(dfs)
    except Exception as e:
        return (f"ERREUR CRITIQUE (Transformation IA): {{e}}", 500)

    cleaned_columns = [re.sub(r'[^a-zA-Z0-9_]+', '_', str(col)).strip('_') for col in result_df.columns]
    final_columns = ['_' + col if col and col[0].isdigit() else col for col in cleaned_columns]
    result_df.columns = final_columns
    
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
    except Exception as e:
        return (f"ERREUR CRITIQUE (Chargement GCS): {{e}}", 500)
        
    return ("ETL complet terminé avec succès.", 200)
"""
    return code


def generate_bigquery_view_code(project_id, dataset_id, view_name, file_name_prefix):
    """Génère le code SQL pour créer une vue BigQuery."""
    final_table_name = file_name_prefix
    return f"""
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.{view_name}` AS (
  SELECT *
  FROM `{project_id}.{dataset_id}.{final_table_name}`
);
"""