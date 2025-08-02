import streamlit as st
import os
import toml
from sqlalchemy import create_engine, text
from google.cloud.sql.connector import Connector
from google.oauth2 import service_account

def get_engine():
    """
    Crée une connexion intelligente qui fonctionne localement ET sur Cloud Run.
    """
    print("DEBUG: Tentative de création du moteur de base de données...")
    
    connector = None
    secrets = {}

    # Si la variable d'env K_SERVICE existe, on est sur Cloud Run.
    if "K_SERVICE" in os.environ:
        print("DEBUG: Environnement Cloud Run détecté.")
        try:
            # Sur Cloud Run, le secret est monté comme un fichier
            with open("/app/.streamlit/secrets.toml", "r") as f:
                secrets = toml.load(f)
            print("-> Fichier secrets.toml chargé depuis le volume monté.")
            # L'authentification est automatique via le compte de service du service Cloud Run
            connector = Connector()
        except Exception as e:
            print(f"❌ Erreur critique sur Cloud Run : Impossible de charger les secrets ou d'initialiser le connecteur. Erreur: {e}")
            return None
    # Sinon, on est en local.
    else:
        print("DEBUG: Environnement local détecté.")
        secrets = st.secrets
        try:
            creds_dict = dict(secrets["firebase_service_account"])
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            connector = Connector(credentials=credentials)
        except Exception as e:
            st.error(f"Erreur d'initialisation du connecteur en local : {e}")
            return None

    # Logique de connexion commune
    try:
        instance_connection_name = secrets["database"]["instance_connection_name"]
        db_user = secrets["database"]["db_user"]
        db_pass = secrets["database"]["db_pass"]
        db_name = secrets["database"]["db_name"]
        print(f"DEBUG: Connexion SQL à '{instance_connection_name}' avec l'utilisateur '{db_user}'.")
        
        def get_conn():
            # Utilisation du pilote psycopg2, plus standard
            conn = connector.connect(
                instance_connection_name,
                "psycopg2",
                user=db_user,
                password=db_pass,
                db=db_name,
            )
            return conn
        
        engine = create_engine("postgresql+psycopg2://", creator=get_conn)
        print("✅ Moteur SQL créé avec succès.")
        return engine
    except Exception as e:
        print(f"❌ Erreur de création du moteur : {e}")
        st.error(f"Erreur de configuration SQL : {e}")
        return None

engine = get_engine()

def init_db():
    """Crée les tables si elles n'existent pas."""
    if not engine:
        raise RuntimeError("ERREUR CRITIQUE : Le moteur de la base de données n'a pas pu être créé.")
    with engine.connect() as connection:
        connection.execute(text("""
        CREATE TABLE IF NOT EXISTS connections (
            id SERIAL PRIMARY KEY, user_id VARCHAR(255) NOT NULL, name VARCHAR(255) NOT NULL,
            url TEXT NOT NULL, db_name VARCHAR(255) NOT NULL, username VARCHAR(255) NOT NULL,
            password_encrypted BYTEA, UNIQUE (user_id, name)
        );"""))
        connection.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL,
            subscription_status VARCHAR(50) DEFAULT 'inactive'
        );"""))
        connection.commit()

def get_or_create_user(user_id: str, email: str):
    """Récupère un utilisateur ou le crée/met à jour de manière atomique."""
    if not engine: return None
    
    with engine.connect() as connection:
        upsert_sql = text("""
            INSERT INTO users (user_id, email)
            VALUES (:user_id, :email)
            ON CONFLICT (email)
            DO UPDATE SET user_id = EXCLUDED.user_id
            RETURNING *;
        """)
        result = connection.execute(upsert_sql, {"user_id": user_id, "email": email}).first()
        connection.commit()
        return dict(result._mapping) if result else None

def update_user_subscription(user_id: str, status: str):
    """Met à jour le statut d'abonnement d'un utilisateur."""
    if not engine: return
    with engine.connect() as connection:
        connection.execute(
            text("UPDATE users SET subscription_status = :status WHERE user_id = :user_id"),
            {"status": status, "user_id": user_id}
        )
        connection.commit()

def load_connections(user_id: str):
    """Charge les connexions Odoo pour un utilisateur spécifique."""
    if not engine or not user_id: return []
    query = text("SELECT * FROM connections WHERE user_id = :user_id ORDER BY name")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"user_id": user_id}).mappings().all()
            return [dict(row) for row in result]
    except Exception as e:
        st.error(f"Erreur lors du chargement des connexions : {e}")
        return []

def save_connection(user_id: str, name: str, url: str, db_name: str, username: str, password: str):
    """Sauvegarde ou met à jour une connexion Odoo pour un utilisateur."""
    from utils.security import encrypt_data
    if not engine or not user_id: return
    encrypted_password = encrypt_data(password)
    upsert_sql = text("""
        INSERT INTO connections (user_id, name, url, db_name, username, password_encrypted)
        VALUES (:user_id, :name, :url, :db_name, :username, :password_encrypted)
        ON CONFLICT (user_id, name)
        DO UPDATE SET
            url = EXCLUDED.url, db_name = EXCLUDED.db_name, username = EXCLUDED.username,
            password_encrypted = EXCLUDED.password_encrypted;
    """)
    try:
        with engine.connect() as connection:
            connection.execute(upsert_sql, {
                "user_id": user_id, "name": name, "url": url,
                "db_name": db_name, "username": username, "password_encrypted": encrypted_password
            })
            connection.commit()
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de la connexion : {e}")