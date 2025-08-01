# Fichier : services/openai_service.py
import streamlit as st
import openai
import json
import PyPDF2

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")

def generate_transformation_plan(user_prompt, uploaded_file):
    """Gère l'appel en 2 étapes à l'IA pour générer le plan de transformation."""
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
            
            # Étape 1: Obtenir les modèles pertinents
            if 'models' not in st.session_state or not st.session_state.get('models'):
                model_data = st.session_state.models_proxy.execute_kw(st.session_state.conn_details['db'], st.session_state.uid, st.session_state.conn_details['password'], 'ir.model', 'search_read', [[]], {'fields': ['model']})
                st.session_state.models = sorted([m['model'] for m in model_data if m.get('model')])

            system_message_step1 = "Tu es un expert Odoo. À partir de l'objectif de l'utilisateur et de la liste complète des modèles, réponds UNIQUEMENT avec un objet JSON contenant une seule clé 'relevant_models' qui est une liste de noms de modèles pertinents."
            response_step1 = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_message_step1}, {"role": "user", "content": f"{full_prompt_for_ai}\n\nModèles disponibles: {st.session_state.models}"}], response_format={"type": "json_object"})
            relevant_models = json.loads(response_step1.choices[0].message.content)['relevant_models']

            # Étape 2: Générer le code de transformation
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