import streamlit as st

st.set_page_config(
    page_title="Tarifs - Odoo AI Transformer",
    page_icon="💰",
    layout="wide"
)

# --- HEADER ---
st.title("Un Tarif Simple pour une Puissance Illimitée")
st.subheader("Concentrez-vous sur l'analyse de vos données, pas sur leur extraction. Notre offre est unique, transparente et sans engagement.")
st.markdown("---")


# --- BLOC DE PRIX CENTRAL ---
# On utilise des colonnes pour centrer joliment le bloc de prix
_, col2, _ = st.columns([1, 2, 1])

with col2:
    st.info("### Offre Unique")
    
    # Utilisation de HTML dans le markdown pour un meilleur style
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>29€</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-weight: bold;'>HT / mois / par base de données connectée</p>", unsafe_allow_html=True)
    
    st.markdown("---")

    st.markdown("""
    #### **Ce qui est inclus pour chaque connexion :**
    
    * ✅ **Connexion Sécurisée** : Vos clés d'API Odoo sont chiffrées avec Google Cloud KMS, le plus haut standard de sécurité.
    * ✅ **Transformations Illimitées** : Décrivez et générez autant de modèles de données que vous le souhaitez.
    * ✅ **Extractions Illimitées** : Exécutez vos pipelines de transformation sans aucune limite d'usage.
    * ✅ **Code de Déploiement Inclus** : Générez en un clic le code de votre Cloud Function et les fichiers nécessaires pour l'automatisation.
    * ✅ **Mises à Jour** : Bénéficiez de toutes les améliorations futures de l'application.
    * ✅ **Support Technique** : Accès à notre support par email pour toute question.
    """)
    st.markdown("---")
    st.button("Connecter ma première base (Bientôt disponible)", type="primary", disabled=True, use_container_width=True)


# --- SECTION EXPLICATIVE ---
st.markdown("---")
st.header("Comment fonctionne le modèle par connexion ?")
st.markdown("""
C'est très simple. Notre modèle est conçu pour s'adapter à votre structure, que vous ayez une ou plusieurs entités à analyser.

-   **Vous avez une seule base de données Odoo ?** Vous souscrivez à un seul abonnement de 29€/mois.
-   **Vous gérez 3 bases de données Odoo distinctes ?** Vous souscrivez à 3 abonnements, un pour chaque base. Vous pouvez gérer toutes vos connexions depuis un seul et même compte utilisateur.

Ce modèle vous garantit que vous ne payez que pour ce que vous utilisez, avec une flexibilité totale.
""")


# --- FOIRE AUX QUESTIONS (FAQ) ---
st.markdown("---")
st.header("Questions Fréquentes")

with st.expander("🔒 Mes données sont-elles en sécurité ?"):
    st.markdown("""
    **La sécurité est notre priorité absolue.**
    1.  **Chiffrement des Clés API** : Vos clés API Odoo ne sont jamais stockées en clair. Elles sont chiffrées via le service **Google Cloud KMS** avant d'être sauvegardées dans notre base de données. Seule notre application, via des permissions très strictes, peut demander le déchiffrement au moment précis d'une connexion à Odoo.
    2.  **Aucun stockage de vos données métier** : Notre application ne stocke **jamais** vos données Odoo (factures, clients, produits...). Elle agit comme un "tuyau" intelligent : elle lit les données, les transforme en mémoire, et les envoie sur votre propre projet Google Cloud. Vos données ne transitent que le temps de la transformation.
    """)

with st.expander("🔄 Puis-je annuler mon abonnement à tout moment ?"):
    st.markdown("""
    **Oui, absolument.** Nos abonnements sont sans engagement. Vous pourrez gérer, ajouter ou annuler vos abonnements à tout moment directement depuis votre tableau de bord (qui sera disponible après l'implémentation de l'authentification). L'annulation prend effet à la fin de la période de facturation en cours.
    """)

with st.expander("🏢 Proposez-vous des offres pour les grandes entreprises ou les agences ?"):
    st.markdown("""
    Oui. Si vous avez besoin de connecter un grand nombre de bases de données (plus de 10) ou si vous êtes une agence qui gère les données de plusieurs clients, contactez-nous. Nous pouvons discuter d'une offre sur mesure avec des tarifs dégressifs et un support dédié.
    """)

with st.expander("⚙️ Y a-t-il des prérequis techniques pour connecter Odoo ?"):
    st.markdown("""
    Le seul prérequis est que votre instance Odoo soit accessible depuis Internet et que vous disposiez des droits d'accès via l'API XML-RPC (ce qui est le cas par défaut pour la plupart des hébergements Odoo). Notre outil est compatible avec les versions Odoo 14, 15, 16 et supérieures.
    """)