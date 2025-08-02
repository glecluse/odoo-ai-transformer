import re
import datetime
from io import StringIO

def generate_gcp_function_code(url, db, username, project_id, file_name_prefix, model_fields_dict, ai_python_code):
    # ... (copiez la fonction generate_gcp_function_code ici) ...
    clean_url = url.rstrip('/')
    secret_name = f"api_key_{db.replace('-', '_')}"
    bucket_name = db.replace('_', '-')
    
    models_to_export_str = "{\n"
    for model, fields in model_fields_dict.items():
        fields_str = ", ".join([f"'{f}'" for f in fields])
        models_to_export_str += f"        '{model}': [{fields_str}],\n"
    models_to_export_str += "    }"
    
    code = f"""# ... (le reste du code de la fonction générée) ..."""
    return code

def generate_bigquery_view_code(project_id, dataset_id, view_name, file_name_prefix):
    # ... (copiez la fonction generate_bigquery_view_code ici) ...
    final_table_name = file_name_prefix
    return f"""
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.{view_name}` AS (
  SELECT *
  FROM `{project_id}.{dataset_id}.{final_table_name}`
);
"""