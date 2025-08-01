# Fichier : test_db.py
import os
import toml
from sqlalchemy import create_engine
from google.cloud.sql.connector import Connector

print("--- DÉBUT DU TEST DE CONNEXION À LA BASE DE DONNÉES ---")

try:
    print("Étape 1 : Lecture du fichier de secrets...")
    # Sur Cloud Run, le secret est monté à cet emplacement
    with open("/app/.streamlit/secrets.toml", "r") as f:
        secrets = toml.load(f)
    print("-> Fichier secrets.toml chargé avec succès.")

    # On récupère les informations de connexion
    instance_connection_name = secrets["database"]["instance_connection_name"]
    db_user = secrets["database"]["db_user"]
    db_pass = secrets["database"]["db_pass"]
    db_name = secrets["database"]["db_name"]
    print("-> Informations de la base de données lues.")

    # On s'authentifie automatiquement via le compte de service de Cloud Run
    print("Étape 2 : Initialisation du connecteur Cloud SQL...")
    connector = Connector()
    print("-> Connecteur initialisé.")

    def get_conn():
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn

    print("Étape 3 : Création du moteur SQLAlchemy...")
    engine = create_engine("postgresql+pg8000://", creator=get_conn)
    print("-> Moteur créé.")

    print("Étape 4 : Tentative de connexion...")
    with engine.connect() as connection:
        print("\n\n✅✅✅ SUCCÈS : Connexion à la base de données établie ! ✅✅✅\n\n")

except Exception as e:
    print(f"\n\n❌❌❌ ÉCHEC : Une erreur est survenue. ❌❌❌")
    print(f"Type d'erreur : {type(e).__name__}")
    print(f"Détails de l'erreur : {e}\n\n")

print("--- FIN DU TEST DE CONNEXION ---")