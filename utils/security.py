# Fichier : utils/security.py
import streamlit as st
import re
from cryptography.fernet import Fernet

SAVED_PASSWORD_PLACEHOLDER = "••••••••••"
FERNET_KEY = st.secrets.get("FERNET_KEY")

if FERNET_KEY:
    FERNET = Fernet(FERNET_KEY.encode())
else:
    FERNET = None

def sanitize_for_gcs(text: str) -> str:
    """Nettoie une chaîne de caractères pour la rendre compatible avec les noms de GCS."""
    if not text:
        return "export-odoo"
    text = text.lower()
    text = text.replace(' ', '-')
    text = re.sub(r'[^\w-]', '', text)
    text = re.sub(r'--+', '-', text)
    text = text.strip('-')
    return text or "export-odoo"

def generate_and_display_key():
    key = Fernet.generate_key().decode()
    st.warning("⚠️ Clé de chiffrement non trouvée !")
    st.info("Veuillez ajouter la ligne suivante à votre fichier `.streamlit/secrets.toml` :")
    st.code(f'FERNET_KEY = "{key}"')
    return None

def encrypt_data(data: str) -> bytes:
    if not FERNET: return None
    return FERNET.encrypt(data.encode())

def decrypt_data(encrypted_data: bytes) -> str:
    if not FERNET or not encrypted_data: return None
    try:
        return FERNET.decrypt(encrypted_data).decode()
    except Exception:
        return None