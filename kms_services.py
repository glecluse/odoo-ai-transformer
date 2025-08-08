import os
import streamlit as st
from google.cloud import kms
from google.api_core import exceptions as google_exceptions

# --- Configuration (ne change pas) ---
PROJECT_ID = os.environ.get("GCP_PROJECT") or os.environ.get("PROJECT_ID") or st.secrets.get("PROJECT_ID")
LOCATION_ID = "europe-west1"
KEY_RING_ID = "odoo-app-keyring"
KEY_ID = "odoo-password-key"
KEY_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION_ID}/keyRings/{KEY_RING_ID}/cryptoKeys/{KEY_ID}"

# On supprime l'initialisation du client d'ici
# kms_client = kms.KeyManagementServiceClient()


def encrypt_password(plaintext: str) -> bytes:
    """Chiffre un mot de passe en utilisant Cloud KMS."""
    # --- MODIFICATION : On initialise le client ici ---
    kms_client = kms.KeyManagementServiceClient()

    if not isinstance(plaintext, str) or not plaintext:
        raise TypeError("Le mot de passe à chiffrer doit être une chaîne de caractères non vide.")

    try:
        plaintext_bytes = plaintext.encode("utf-8")
        response = kms_client.encrypt(name=KEY_NAME, plaintext=plaintext_bytes)
        return response.ciphertext
    except google_exceptions.PermissionDenied as e:
        st.error("Permission refusée pour chiffrer avec KMS. Vérifiez les droits IAM.")
        raise
    except Exception as e:
        print(f"Erreur inattendue lors du chiffrement KMS: {e}")
        raise


def decrypt_password(ciphertext: bytes) -> str:
    """Déchiffre un mot de passe en utilisant Cloud KMS."""
    # --- MODIFICATION : On initialise le client ici aussi ---
    kms_client = kms.KeyManagementServiceClient()
    
    if not isinstance(ciphertext, bytes):
        raise TypeError("Le texte chiffré doit être de type bytes.")

    try:
        response = kms_client.decrypt(name=KEY_NAME, ciphertext=ciphertext)
        return response.plaintext.decode("utf-8")
    except google_exceptions.PermissionDenied as e:
        st.error("Permission refusée pour déchiffrer avec KMS. Vérifiez les droits IAM.")
        raise
    except Exception as e:
        print(f"Erreur inattendue lors du déchiffrement KMS: {e}")
        raise