# pages/2_💶_Tarifs.py

import streamlit as st

st.set_page_config(layout="centered", page_title="Tarifs")

st.title("Un tarif simple et transparent")
st.subheader("Concentrez-vous sur vos données, pas sur des plans compliqués.")

st.markdown("---")

# Utilisation de colonnes pour créer un effet de "carte" centrée
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown(
        """
        <div style="
            border: 2px solid #28a745;
            border-radius: 10px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        ">
            <h2 style="color: #28a745;">Plan Unique</h2>
            <p style="font-size: 3em; font-weight: bold; margin: 0;">29€ <span style="font-size: 0.5em; color: grey;">HT / mois</span></p>
            <p style="color: grey; margin-bottom: 20px;">Par base de données Odoo connectée</p>
            <hr>
            <ul style="text-align: left; list-style-position: inside;">
                <li>✅ Extractions de données illimitées</li>
                <li>✅ Génération de code par IA (GPT-4o)</li>
                <li>✅ Génération d'artefacts Google Cloud</li>
                <li>✅ Support par email</li>
                <li>✅ Mises à jour incluses</li>
            </ul>
            <br>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("") # Espace
    # Bouton d'appel à l'action qui redirige vers la page de connexion/inscription
    if st.button("🚀 Commencer maintenant", use_container_width=True, type="primary"):
        st.switch_page("app.py")


st.markdown("---")
st.info("💡 **Comment ça fonctionne ?** Un abonnement vous donne le droit de connecter une base de données Odoo. Si vous gérez plusieurs entreprises avec des bases de données Odoo distinctes, vous pouvez souscrire à plusieurs abonnements depuis le même compte utilisateur.")