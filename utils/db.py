import streamlit as st
import os
from sqlalchemy import create_engine, text
from google.cloud.sql.connector import Connector
from google.oauth2 import service_account

def get_engine():
    """Crée une connexion intelligente qui fonctionne localement ET sur Cloud Run."""
    
    # Si la variable d'env K_SERVICE existe, on est sur Cloud Run.
    # L'authentification est automatique via le compte de service du service Cloud Run.
    if "K_SERVICE" in os.environ:
        connector = Connector()
    # Sinon, on est en local. On utilise le fichier de service account des secrets.
    else:
        try:
            creds_dict = dict(st.secrets["firebase_service_account"])
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            connector = Connector(credentials=credentials)
        except Exception as e:
            st.error(f"Erreur d'initialisation du connecteur en local : {e}")
            return None

    # Logique de connexion commune
    try:
        instance_connection_name = st.secrets["database"]["instance_connection_name"]
        db_user = st.secrets["database"]["db_user"]
        db_pass = st.secrets["database"]["db_pass"]
        db_name = st.secrets["database"]["db_name"]
        def get_conn():
            conn = connector.connect(
                instance_connection_name, "pg8000",
                user=db_user, password=db_pass, db=db_name
            )
            return conn
        engine = create_engine("postgresql+pg8000://", creator=get_conn)
        return engine
    except Exception as e:
        st.error(f"Erreur de configuration de la base de données. Vérifiez vos secrets. Erreur: {e}")
        return None

engine = get_engine()

def init_db():
    """Crée les tables si elles n'existent pas."""
    if not engine:
        raise RuntimeError("La connexion à la base de données a échoué. L'application ne peut pas démarrer.")
    with engine.connect() as connection:
        connection.execute(text("""
        CREATE TABLE IF NOT EXISTS connections (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            url TEXT NOT NULL,
            db_name VARCHAR(255) NOT NULL,
            username VARCHAR(255) NOT NULL,
            password_encrypted BYTEA,
            UNIQUE (user_id, name)
        );
        """))
        connection.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            subscription_status VARCHAR(50) DEFAULT 'inactive'
        );
        """))
        connection.commit()

def get_or_create_user(user_id: str, email: str):
    """Récupère un utilisateur ou le crée s'il n'existe pas de manière très robuste."""
    if not engine: return None
    
    with engine.connect() as connection:
        # Étape 1: On essaie de récupérer l'utilisateur par son ID unique de Firebase
        user = connection.execute(text("SELECT * FROM users WHERE user_id = :user_id"), {"user_id": user_id}).first()
        if user:
            return dict(user._mapping)

        # Étape 2: S'il n'existe pas, on tente de l'insérer SANS METTRE À JOUR
        # ON CONFLICT (email) DO NOTHING gère le cas où l'e-mail existe déjà avec un autre user_id
        insert_sql = text("""
            INSERT INTO users (user_id, email)
            VALUES (:user_id, :email)
            ON CONFLICT (email) DO NOTHING;
        """)
        connection.execute(insert_sql, {"user_id": user_id, "email": email})
        connection.commit() # On s'assure que l'insertion est bien terminée

        # Étape 3: On relit OBLIGATOIREMENT les données depuis la base en utilisant l'e-mail.
        # Soit on trouve l'utilisateur qu'on vient d'insérer, soit on trouve l'utilisateur
        # existant qui avait cet e-mail (et on utilisera son user_id existant).
        final_user = connection.execute(
            text("SELECT * FROM users WHERE email = :email"), {"email": email}
        ).first()

        if final_user:
             return dict(final_user._mapping)
        else:
            # Ce cas ne devrait JAMAIS arriver, mais c'est une sécurité
            st.error("Une erreur critique est survenue lors de la création de votre profil utilisateur.")
            return None

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
            url = EXCLUDED.url,
            db_name = EXCLUDED.db_name,
            username = EXCLUDED.username,
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