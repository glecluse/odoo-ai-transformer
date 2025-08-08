# Odoo AI Transformer 🚀

Une application web pour transformer vos données Odoo en pipelines de données automatisés sur GCP en utilisant le langage naturel. Fini les exports CSV manuels, décrivez simplement votre besoin et laissez l'IA construire l'infrastructure pour vous.

![Status](https://img.shields.io/badge/status-en%20développement-orange)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Framework](https://img.shields.io/badge/framework-Streamlit-red)
![Licence](https://img.shields.io/badge/licence-MIT-green)

[Image of the Odoo AI Transformer app in action]

## 🎯 Le Problème

Extraire et analyser des données d'un ERP comme Odoo est souvent une tâche complexe qui nécessite :
-   Une connaissance approfondie du modèle de données d'Odoo.
-   Des compétences techniques en Python, SQL et dans les API.
-   Des processus d'export/import manuels, chronophages et sources d'erreurs.
-   La mise en place d'une infrastructure de données (ETL) complexe pour l'automatisation.

## ✨ Notre Solution

**Odoo AI Transformer** agit comme un "traducteur" entre vos besoins métier et l'infrastructure technique. L'application vous permet de :

1.  **Décrire** un rapport en langage naturel (ex: "Je veux le chiffre d'affaires par commercial pour le dernier trimestre").
2.  **Générer** automatiquement un plan d'extraction et un script de transformation Python/Pandas grâce à l'IA (GPT-4o).
3.  **Valider** les données via un aperçu dans l'application.
4.  **Déployer** en quelques clics un pipeline de données complet et automatisé sur votre propre projet Google Cloud Platform.

Le résultat final est une **vue BigQuery** toujours à jour, prête à être connectée à vos outils de Business Intelligence préférés (Looker Studio, Power BI, Tableau, etc.).

---

## 🏗️ Architecture

L'application se compose de deux flux principaux : l'interface de configuration (le dialogue avec l'IA) et le pipeline de données déployé sur GCP.

```mermaid
graph TD
    subgraph "Phase 1: Utilisation de l'Application Streamlit"
        A[Utilisateur] -->|1. Décrit son besoin| B(Application Streamlit);
        B -->|2. Interroge l'IA| C[OpenAI API];
        C -->|3. Retourne un plan de code| B;
        B -->|4. Extrait les données Odoo| D[API Odoo];
        D -->|5. Affiche un aperçu| B;
        B -->|6. Génère les artefacts de déploiement| E[Code Cloud Function, SQL, etc.];
    end

    subgraph "Phase 2: Pipeline de Données Déployé sur GCP"
        F[Cloud Scheduler] -->|7. Déclenche la fonction chaque jour| G(Cloud Function);
        G -->|8. Extrait les données| D;
        G -->|9. Écrit un fichier Parquet| H[Cloud Storage];
        I[BigQuery Data Transfer] -->|10. Charge le fichier| H;
        I -->|11. Met à jour la table| J[Table Native BigQuery];
        K[Outil de BI] -->|12. Interroge la vue| L[Vue BigQuery];
        L --> J;
    end