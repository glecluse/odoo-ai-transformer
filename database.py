import os
import streamlit as st
import sqlalchemy
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    UniqueConstraint,
    LargeBinary,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from google.cloud.sql.connector import Connector

# SQLAlchemy declarative base, qui sert de registre pour nos modèles de table
Base = declarative_base()

# Définition de notre table "connections" via une classe Python (ORM)
class Connection(Base):
    __tablename__ = "connections"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    url = Column(String(255), nullable=False)
    db_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    encrypted_password = Column(LargeBinary, nullable=False)
    
    UniqueConstraint("name")

# Initialisation du connecteur Cloud SQL (ne fait rien s'il n'est pas utilisé)
connector = Connector()

def get_engine():
    """
    Crée et retourne le moteur de connexion SQLAlchemy.
    Cette fonction est "hybride" : elle s'adapte à l'environnement d'exécution.
    """
    
    # Cherche d'abord dans les variables d'environnement (pour Cloud Run)
    # Si non trouvé, cherche dans les secrets de Streamlit (pour le local)
    db_user = os.environ.get("DB_USER") or st.secrets.get("DB_USER")
    db_pass = os.environ.get("DB_PASS") or st.secrets.get("DB_PASS")
    db_name = os.environ.get("DB_NAME") or st.secrets.get("DB_NAME")
    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME") or st.secrets.get("INSTANCE_CONNECTION_NAME")

    if not all([db_user, db_pass, db_name, instance_connection_name]):
        st.error("Les informations de connexion à la base de données ne sont pas complètes. Vérifiez vos variables d'environnement ou le fichier secrets.toml.")
        st.stop()

    def getconn():
        # Le connecteur gère la connexion sécurisée via un tunnel IAM
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn

    # Création du moteur qui utilisera la fonction getconn pour chaque nouvelle connexion
    engine = create_engine("postgresql+pg8000://", creator=getconn)
    return engine

# Création du moteur global et de la fabrique de sessions pour l'application
engine = get_engine()
Session = sessionmaker(bind=engine)

def init_db():
    """
    Crée toutes les tables définies dans Base (ici, juste la table 'connections')
    si elles n'existent pas déjà dans la base de données.
    """
    Base.metadata.create_all(engine)

def load_connections():
    """Charge toutes les connexions depuis la base de données."""
    session = Session()
    try:
        connections = session.query(Connection).order_by(Connection.name).all()
        # Convertit la liste d'objets Connection en une liste de dictionnaires
        return [
            {
                "id": c.id, "name": c.name, "url": c.url, 
                "db_name": c.db_name, "username": c.username,
                "encrypted_password": c.encrypted_password
            } for c in connections
        ]
    finally:
        # S'assure que la session est bien fermée pour libérer la connexion
        session.close()

def save_connection(name, url, db_name, username, encrypted_password):
    """Sauvegarde (INSERT) ou met à jour (UPDATE) une connexion."""
    session = Session()
    try:
        # Cherche si une connexion avec ce nom existe déjà
        existing_conn = session.query(Connection).filter_by(name=name).one_or_none()
        
        if existing_conn:
            # Si elle existe, on met à jour ses champs
            existing_conn.url = url
            existing_conn.db_name = db_name
            existing_conn.username = username
            existing_conn.encrypted_password = encrypted_password
        else:
            # Sinon, on crée un nouvel objet et on l'ajoute à la session
            new_conn = Connection(
                name=name, url=url, db_name=db_name, 
                username=username, encrypted_password=encrypted_password
            )
            session.add(new_conn)
        
        # Valide la transaction
        session.commit()
    except:
        # En cas d'erreur, annule la transaction
        session.rollback()
        raise
    finally:
        # S'assure que la session est bien fermée
        session.close()