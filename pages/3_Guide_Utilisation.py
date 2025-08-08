# pages/2_📖_Guide_d_Utilisation.py

import streamlit as st

st.set_page_config(layout="wide", page_title="Guide d'Utilisation - Odoo AI Transformer")

# --- Gardien d'Authentification ---
if not st.session_state.get('is_logged_in', False):
    st.error("🔒 Accès réservé aux utilisateurs connectés.")
    st.info("Veuillez vous connecter depuis la page d'accueil pour accéder à ce guide.")
    st.page_link("app.py", label="Retour à l'accueil", icon="🏠")
    st.stop()
# --- Fin du Gardien ---


st.title("📖 Guide Complet : de Zéro à votre Dashboard Automatisé")
st.markdown("""
Ce guide vous accompagne à chaque étape du processus, depuis la configuration initiale de votre environnement Google Cloud jusqu'à l'automatisation complète de votre pipeline de données Odoo, **le tout depuis l'interface web de la console GCP**.
""")

st.divider()

# ==============================================================================
# PHASE 1 : PRÉREQUIS GCP
# ==============================================================================
st.header("Phase 1 : Prérequis - Votre Compte Google Cloud (GCP)")
st.warning("Cette phase est à réaliser **une seule fois**. Si votre projet GCP est déjà prêt, vous pouvez passer à la phase 2.", icon="☝️")

with st.expander("Cliquez ici pour le détail de la configuration initiale de GCP"):
    
    st.subheader("A. Créer ou accéder à votre compte GCP")
    st.markdown("""
    1.  **Compte et Projet :** Assurez-vous d'avoir un [compte Google Cloud](https://console.cloud.google.com/) avec un projet créé et un compte de facturation associé.
    2.  **Activer les API :** Dans la console, cherchez et activez les services suivants : `Cloud Functions`, `Cloud Build`, `Secret Manager`, `BigQuery API`, `Cloud Scheduler API`, et `BigQuery Data Transfer Service`.
    """)

# ==============================================================================
# PHASE 2 : UTILISATION DE L'APPLICATION
# ==============================================================================
st.header("Phase 2 : Utilisation de l'Application")
st.markdown("""
Sur la page **Application**, suivez le flux complet :
1.  **Connectez-vous à Odoo**.
2.  **Décrivez votre besoin** et générez le plan de transformation.
3.  **Exécutez le plan**. Cela va extraire les données d'Odoo et les déposer dans un fichier sur votre **Google Cloud Storage**.
4.  **Générez les artefacts GCP**. L'application vous fournira tout le code et les commandes nécessaires. Gardez cet onglet ouvert.
""")

st.divider()

# ==============================================================================
# PHASE 3 : DÉPLOIEMENT SUR GCP
# ==============================================================================
st.header("Phase 3 : Déploiement sur votre projet GCP")
st.success("Vous allez maintenant configurer votre infrastructure sur GCP en utilisant les artefacts générés.")

st.subheader("Étape 5 : Créer le Secret pour le mot de passe Odoo")
st.markdown("""
1.  **Ouvrir le Cloud Shell :** En haut à droite de la console Google Cloud, cliquez sur l'icône **[>_]** ("Activer Cloud Shell").
2.  **Copier et coller la commande :** Copiez la commande `gcloud secrets create ...` fournie par l'application et collez-la dans le Cloud Shell. Appuyez sur **Entrée** et autorisez si nécessaire. Votre clé API est maintenant stockée en toute sécurité.
""")

st.subheader("Étape 6 : Déployer la Cloud Function")
st.markdown("""
Suivez les étapes pour créer une **Cloud Function** depuis la console, en utilisant le code `main.py` et `requirements.txt` fournis par l'application. N'oubliez pas l'étape cruciale : donner au **compte de service** de la fonction le rôle **`Accesseur de secrets de Secret Manager`** sur le secret que vous venez de créer.
""")

st.subheader("Étape 7 : Création de la Table et de la Vue dans BigQuery")
st.markdown("""
**A. Créer une table native depuis Cloud Storage (chargement initial)**
1.  Allez dans la console **[BigQuery](https://console.cloud.google.com/bigquery)**.
2.  Dans le panneau "Explorateur", trouvez votre projet, cliquez sur les trois points à côté de votre ensemble de données (dataset) et choisissez **"Créer une table"**.
3.  Remplissez le formulaire de création :
    - **Créer une table à partir de :** `Google Cloud Storage`.
    - **Sélectionner le fichier depuis le bucket GCS :** Cliquez sur "Parcourir". Naviguez et sélectionnez le fichier `.parquet` généré par la fonction.
    - **Format du fichier :** `Parquet`.
    - **Table :** Donnez un nom à votre table de données brutes (ex: `odoo_ventes_raw`).
    - **Schéma :** Cochez la case **"Détection automatique"**.
4.  Cliquez sur **"Créer une table"**.

**B. Créer la vue par-dessus la table**
1.  Maintenant, copiez le code SQL pour la **"Vue BigQuery"** généré par notre application.
2.  Collez cette requête dans l'éditeur de requêtes de BigQuery et cliquez sur **"Exécuter"**.
""")


# ==============================================================================
# PHASE 4 : AUTOMATISATION
# ==============================================================================
st.header("Phase 4 : Automatisation Complète du Pipeline")

st.subheader("A. Automatiser l'exécution de la Cloud Function (Cloud Scheduler)")
st.markdown("""
Cette tâche va extraire les données d'Odoo chaque jour.
1.  Allez dans **[Cloud Scheduler](https://console.cloud.google.com/cloudscheduler)** et créez une tâche.
2.  **Fréquence :** `0 5 * * *` (tous les jours à 5h du matin).
3.  **Cible :** `HTTP`, avec l'URL de votre Cloud Function.
4.  **Authentification :** `Ajouter un jeton OIDC`, avec le compte de service de votre fonction.
""")

st.subheader("B. Automatiser le transfert de Cloud Storage vers BigQuery")
st.markdown("""
Cette seconde tâche va automatiquement mettre à jour votre table BigQuery avec le nouveau fichier déposé par la Cloud Function.
1.  Allez dans la console **[BigQuery Data Transfer Service](https://console.cloud.google.com/bigquery/transfers)** et cliquez sur **"CRÉER UN TRANSFERT"**.
2.  **Source :** `Google Cloud Storage`.
3.  **Planification :** Choisissez une heure **postérieure** à celle de la Cloud Function (ex: "Tous les jours à 6h00").
4.  **Paramètres de destination :**
    - **Table :** Entrez le nom de la table native que vous avez créée (ex: `odoo_ventes_raw`).
    - **Préférence d'écriture :** **`Overwrite`** (Écraser).
5.  **Détails de la source de données :**
    - **Chemin Cloud Storage :** Indiquez le chemin vers votre fichier, avec un joker (ex: `gs://VOTRE_BUCKET/rapport_ventes_mensuel.parquet`).
6.  Cliquez sur **"Enregistrer"**.
""")

st.divider()

# ==============================================================================
# PHASE 5 : VISUALISATION
# ==============================================================================
st.header("Phase 5 : Connexion de votre Outil de Business Intelligence")
st.markdown("Félicitations ! 🚀 Votre pipeline est 100% fonctionnel et automatisé. La dernière étape est la plus gratifiante : connecter votre outil de BI à la **vue BigQuery** que vous avez créée.")
st.info("Choisissez votre outil dans la liste ci-dessous pour obtenir un guide de connexion détaillé.")

tool_options = [
    "Sélectionnez un outil...",
    "Looker Studio",
    "Microsoft Power BI",
    "Tableau",
    "Metabase",
    "Qlik Sense",
    "Google Sheets",
    "Autre outil (générique)"
]
selected_tool = st.selectbox("Choisissez votre outil de visualisation :", tool_options)

if selected_tool == "Looker Studio":
    st.success("""
    **Mode Opératoire pour Looker Studio :**
    1.  Ouvrez [Looker Studio](https://lookerstudio.google.com/).
    2.  Cliquez sur **Créer > Source de données**.
    3.  Sélectionnez le connecteur **BigQuery**.
    4.  Naviguez jusqu'à votre **Projet GCP > Dataset > Vue** pour la sélectionner.
    5.  Cliquez sur **Associer**.
    """)

elif selected_tool == "Microsoft Power BI":
    st.success("""
    **Mode Opératoire pour Microsoft Power BI :**
    1.  Dans Power BI Desktop, cliquez sur **Obtenir des données > Google BigQuery**.
    2.  Authentifiez-vous avec votre compte Google.
    3.  Dans le "Navigateur", trouvez votre **Projet > Dataset > Vue** et cochez-la.
    4.  Cliquez sur **Charger**.
    """)

elif selected_tool == "Tableau":
    st.success("""
    **Mode Opératoire pour Tableau :**
    1.  Dans Tableau, sous "Se connecter", choisissez **Google BigQuery**.
    2.  Authentifiez-vous avec votre compte Google.
    3.  Sélectionnez votre **Projet de facturation > Projet > Dataset** et faites glisser votre **Vue** dans l'espace de travail.
    """)

elif selected_tool == "Metabase":
    st.success("""
    **Mode Opératoire pour Metabase :**
    *Prérequis : Avoir un fichier JSON de clé de compte de service GCP.*
    1.  Dans **Admin > Bases de données > Ajouter une base de données**.
    2.  Choisissez **Google BigQuery**.
    3.  Importez votre fichier JSON de clé et spécifiez les datasets à scanner.
    4.  Cliquez sur **Enregistrer**.
    """)

elif selected_tool == "Qlik Sense":
    st.success("""
    **Mode Opératoire pour Qlik Sense :**
    1.  Dans le **Gestionnaire de données**, cliquez sur **Ajouter des données**.
    2.  Sélectionnez le connecteur **Google BigQuery**.
    3.  Après vous être authentifié, sélectionnez votre projet, dataset et la vue à charger.
    """)

elif selected_tool == "Google Sheets":
    st.success("""
    **Mode Opératoire pour Google Sheets :**
    1.  Dans un nouveau Google Sheet, allez dans **Données > Connecteurs de données > Se connecter à BigQuery**.
    2.  Sélectionnez votre projet et trouvez votre vue.
    3.  Importez les données.
    """)

elif selected_tool == "Autre outil (générique)":
    st.warning("""
    **Principe Général de Connexion :**
    1.  Cherchez le connecteur **"Google BigQuery"** dans votre outil.
    2.  Authentifiez-vous.
    3.  Naviguez ou spécifiez le chemin vers votre vue : `ID_Projet.ID_Dataset.Nom_Vue`.
    """)