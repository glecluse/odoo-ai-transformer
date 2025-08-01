# Fichier : services/gcp_service.py
import inspect
import json
import re
from io import StringIO
from utils.odoo import extract_and_process_odoo_data

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