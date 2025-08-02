import os
import sqlalchemy
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    UniqueConstraint,
    LargeBinary # <-- MODIFIÉ : Import à ajouter
)
from sqlalchemy.orm import sessionmaker, declarative_base
from google.cloud.sql.connector import Connector

# SQLAlchemy declarative base
Base = declarative_base()

# Définition de notre table "connections" via SQLAlchemy
class Connection(Base):
    __tablename__ = "connections"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    url = Column(String(255), nullable=False)
    db_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    encrypted_password = Column(LargeBinary, nullable=False) # <-- MODIFIÉ : Nouvelle colonne
    
    UniqueConstraint("name")

# Initialisation du connecteur Cloud SQL
connector = Connector()

def get_engine():
    """Crée et retourne le moteur de connexion SQLAlchemy."""
    
    # Récupération des variables d'environnement qui seront fournies par Cloud Run
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]

    def getconn():
        # Le connecteur gère la connexion sécurisée
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn

    engine = create_engine("postgresql+pg8000://", creator=getconn)
    return engine

# Création du moteur global pour l'application
engine = get_engine()
Session = sessionmaker(bind=engine)

def init_db():
    """Crée toutes les tables dans la base de données."""
    Base.metadata.create_all(engine)

def load_connections():
    """Charge toutes les connexions depuis la base de données."""
    session = Session()
    try:
        connections = session.query(Connection).order_by(Connection.name).all()
        # Convertit les objets en dictionnaires pour correspondre à l'ancien format
        return [
            {
                "id": c.id, "name": c.name, "url": c.url, 
                "db_name": c.db_name, "username": c.username,
                # On ajoute la clé chiffrée pour la passer à la session
                "encrypted_password": c.encrypted_password
            } for c in connections
        ]
    finally:
        session.close()

# <-- MODIFIÉ : La signature et la logique de la fonction ont changé
def save_connection(name, url, db_name, username, encrypted_password):
    """Sauvegarde ou met à jour une connexion."""
    session = Session()
    try:
        # Cherche si une connexion avec ce nom existe déjà
        existing_conn = session.query(Connection).filter_by(name=name).one_or_none()
        
        if existing_conn:
            # Mise à jour
            existing_conn.url = url
            existing_conn.db_name = db_name
            existing_conn.username = username
            existing_conn.encrypted_password = encrypted_password # Mettre à jour aussi
        else:
            # Création
            new_conn = Connection(
                name=name, url=url, db_name=db_name, 
                username=username, encrypted_password=encrypted_password
            )
            session.add(new_conn)
        
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()