# pages/1_❓_Présentation_et_FAQ.py

import streamlit as st

st.set_page_config(layout="wide", page_title="Présentation & FAQ")

# --- Section Présentation ---
st.title("Transformez vos données Odoo en décisions stratégiques, sans écrire une ligne de code.")
st.subheader("Odoo AI Transformer est l'outil qui connecte votre ERP à la puissance de l'analyse de données sur Google Cloud.")

st.markdown("""
---
Vous avez des données précieuses dans Odoo, mais les extraire et les analyser est complexe, chronophage et nécessite des compétences techniques ? 
Notre application révolutionne ce processus. Décrivez simplement en français ce que vous cherchez, et notre IA génère pour vous le pipeline de données complet.
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("⏱️ Temps Économisé", "90%", "sur la création de rapports")
    st.markdown("**Devenez autonome.** Ne dépendez plus des équipes techniques pour accéder à vos données.")
with col2:
    st.metric("💻 Complexité Réduite", "0 Ligne", "de code à écrire")
    st.markdown("**Parlez, ne codez pas.** Notre IA traduit vos besoins en langage naturel en code Python/Pandas robuste.")
with col3:
    st.metric("🔒 Sécurité & Scalabilité", "GCP", "Google Cloud Platform")
    st.markdown("**Prêt pour l'avenir.** Générez des solutions (Cloud Functions, BigQuery) qui évoluent avec votre entreprise.")

st.markdown("""
<br>
""", unsafe_allow_html=True)

# --- Section FAQ ---
st.header("Foire Aux Questions (FAQ)")

with st.expander("❓ **Qu'est-ce que Odoo AI Transformer exactement ?**"):
    st.write("""
     C'est une application web qui vous permet de construire des flux de données (ETL) depuis votre ERP Odoo vers Google Cloud Platform. 
     Vous décrivez votre besoin en langage simple (ex: "Je veux la liste des factures impayées de plus de 30 jours avec le nom du client et le montant") 
     et une IA (GPT-4o) génère le code Python nécessaire pour extraire et transformer ces données. L'application génère ensuite les artefacts nécessaires pour déployer ce flux sur GCP.
     """)

with st.expander("🔐 **La connexion à mon Odoo et mes données sont-elles en sécurité ?**"):
    st.write("""
     Absolument. La sécurité est notre priorité. 
     - Vos mots de passe et clés API Odoo sont chiffrés avec le service **Google Cloud KMS** avant d'être stockés en base de données. Personne, pas même nous, ne peut y accéder en clair.
     - Toutes les communications sont sécurisées.
     - L'application ne stocke aucune de vos données métier (clients, factures, etc.), elle ne fait que les transiter durant le traitement que vous lancez.
     """)

with st.expander("🤔 **Dois-je savoir coder ou connaître Google Cloud Platform ?**"):
    st.write("""
     Non ! C'est tout l'intérêt de l'application. Vous n'avez besoin d'aucune connaissance en Python, Pandas, ou GCP. 
     Vous décrivez votre besoin, validez le plan de l'IA, et l'application vous fournit les fichiers et commandes prêts à l'emploi pour le déploiement.
     """)

with st.expander("📈 **Une fois les données extraites, que puis-je en faire ?**"):
    st.write("""
     L'application stocke vos données transformées dans **Google BigQuery**, un entrepôt de données puissant et universel.
     À partir de là, les possibilités sont infinies, car vous pouvez connecter l'outil que votre entreprise utilise déjà :
     - **Visualisation de Données :** Branchez vos outils de BI favoris comme **Microsoft Power BI, Tableau, ou Looker Studio** pour créer des tableaux de bord interactifs.
     - **Analyse Ad-hoc :** Explorez les données directement avec Google Sheets via le connecteur natif.
     - **Science des Données :** Entraînez des modèles de Machine Learning avec BigQuery ML ou Vertex AI pour des analyses prédictives.
     """)

with st.expander("⚙️ **Quelles sont les versions d'Odoo supportées ?**"):
    st.write("""
     Notre application utilise l'API XML-RPC standard d'Odoo, qui est stable depuis de nombreuses années. Elle est compatible avec toutes les versions récentes d'Odoo (v12, v13, v14, v15, v16, v17+), qu'elles soient Community ou Enterprise, en ligne (Odoo.sh) ou auto-hébergées.
     """)