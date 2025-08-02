import streamlit as st

st.set_page_config(
    page_title="Odoo AI Transformer - Accueil",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Odoo AI Transformer : Transformez vos données Odoo avec l'IA")

st.header("Bienvenue sur l'outil qui connecte votre ERP Odoo à l'intelligence artificielle.")
st.markdown("""
Cette application a été conçue pour simplifier radicalement l'extraction et la transformation de vos données Odoo. 
Fini les scripts complexes et les exports manuels fastidieux. Décrivez simplement en langage naturel le tableau de données que vous souhaitez obtenir, et laissez l'IA faire le reste.
""")

st.subheader("Comment ça fonctionne ?")

col1, col2, col3 = st.columns(3)

with col1:
    st.info("1. Connexion Sécurisée")
    st.markdown("""
    Connectez-vous à une ou plusieurs de vos bases de données Odoo. Vos clés d'API sont chiffrées de bout en bout grâce à Google Cloud KMS, garantissant une sécurité de niveau entreprise.
    """)

with col2:
    st.success("2. Description Intelligente")
    st.markdown("""
    Rendez-vous sur la page **Application**. Décrivez votre besoin en français ("Je veux la liste des factures impayées de plus de 30 jours avec le nom du client et le montant") ou téléchargez un cahier des charges.
    """)

with col3:
    st.warning("3. Génération et Déploiement")
    st.markdown("""
    L'IA analyse votre demande, identifie les modèles Odoo pertinents et génère le code de transformation. Vous pouvez ensuite valider et déployer ce pipeline de données en un clic sur Google Cloud.
    """)

st.info("Pour commencer, sélectionnez **🚀 Application** dans le menu de navigation à gauche.")