# Fichier : pages/1_Comment_ça_marche.py
import streamlit as st

def show_how_it_works_page():
    """
    Affiche le contenu de la page expliquant le fonctionnement de l'application.
    """
    st.set_page_config(layout="wide", page_title="Comment ça marche", page_icon="❓")

    st.markdown("""
    # Bienvenue sur l'Odoo AI Data Transformer 🚀
    
    ### Votre assistant pour transformer vos données Odoo en insights, sans écrire une seule ligne de code.
    
    Vous avez des données précieuses dans Odoo, mais les extraire et les préparer pour vos analyses est un processus complexe, lent et coûteux ? Oubliez les scripts sur mesure et les exports CSV manuels. Notre assistant utilise l'intelligence artificielle pour vous permettre de construire des flux de données automatisés, simplement en décrivant vos besoins.
    
    ---
    
    ## Le fonctionnement en 3 étapes simples
    
    Notre processus est conçu pour vous guider de votre question métier à un tableau de bord prêt à l'emploi en quelques minutes.
    
    ### 1. ✍️ Décrivez votre besoin
    
    Connectez-vous à votre base de données Odoo en toute sécurité depuis la page principale (`app.py`), puis utilisez notre formulaire guidé pour expliquer le tableau de données que vous souhaitez obtenir. Parlez à l'IA comme vous parleriez à un analyste de données :
    
    * **Quel est le sujet ?** ("*Le chiffre d'affaires mensuel par commercial*")
    * **Quelles sont les métriques ?** ("*La somme des montants totaux, le nombre de commandes*")
    * **Comment regrouper ?** ("*Par mois et par vendeur*")
    * **Quels filtres appliquer ?** ("*Uniquement les commandes de l'année en cours et celles qui sont confirmées*")
    
    Plus vous êtes précis, plus le résultat sera pertinent !
    
    ### 2. ✅ Validez le plan de l'IA
    
    Une fois votre demande soumise, notre assistant intelligent se met au travail :
    * Il analyse votre besoin et le couple au schéma technique de votre base de données Odoo.
    * Il identifie les modèles et les champs pertinents à extraire.
    * Il génère un **plan de transformation complet**, y compris le code Python/Pandas qui sera utilisé.
    
    Ce plan vous est présenté de manière claire et transparente. **Vous avez le contrôle total** et pouvez valider l'approche de l'IA avant d'exécuter quoi que ce soit.
    
    ### 3. 🚀 Exécutez et Déployez
    
    Une fois le plan validé, l'action commence :
    * **Prévisualisez :** Exécutez le plan en un clic pour extraire et transformer les données. Un aperçu du tableau final s'affiche directement dans l'application.
    * **Générez le package Cloud :** Si le résultat vous convient, cliquez sur "Générer". L'application produit alors tout ce dont vous avez besoin pour automatiser ce flux de données sur Google Cloud Platform, y compris des instructions pas-à-pas pour construire votre dashboard dans Looker Studio !
    
    ---
    
    ## Principaux Avantages
    
    * **Simplicité Radicale :** Plus besoin de compétences techniques. Si vous pouvez décrire un rapport, vous pouvez construire un pipeline de données.
    * **Rapidité Inégalée :** Passez de l'idée au déploiement en quelques minutes, au lieu de jours ou de semaines.
    * **Puissance de l'IA :** Profitez d'un code de transformation optimisé, généré par une IA.
    * **Automatisation Complète :** Déployez une fonction qui rafraîchira vos données automatiquement.
    * **Sécurité :** Vos identifiants de connexion sont systématiquement chiffrés.
    
    ---
    
    ### Prêt à transformer vos données ?
    
    Retournez sur la page d'accueil **(app)** pour connecter votre base de données Odoo et lancer votre première transformation !
    """)

# Appel de la fonction pour afficher la page
show_how_it_works_page()