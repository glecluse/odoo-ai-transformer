import os
import streamlit as st
from google.cloud import kms
from google.api_core import exceptions as google_exceptions

# Initialisation du client KMS. 
# En local, il utilisera les identifiants de votre `gcloud auth application-default login`.
# Sur Cloud Run, il utilisera automatiquement les identifiants du compte de service.
kms_client = kms.KeyManagementServiceClient()

# --- Configuration récupérée depuis l'environnement ou les secrets ---

# Sur Cloud Run, la variable GCP_PROJECT est injectée automatiquement.
# En local, on se rabat sur la variable PROJECT_ID que nous avons mise dans secrets.toml
PROJECT_ID = os.environ.get("GCP_PROJECT") or os.environ.get("PROJECT_ID") or st.secrets.get("PROJECT_ID")

# Ces valeurs sont fixes pour notre infrastructure, on peut les laisser en dur.
LOCATION_ID = "europe-west1"
KEY_RING_ID = "odoo-app-keyring"
KEY_ID = "odoo-password-key"

# Construction du nom complet de la ressource de la clé, qui est son identifiant unique
KEY_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION_ID}/keyRings/{KEY_RING_ID}/cryptoKeys/{KEY_ID}"


def encrypt_password(plaintext: str) -> bytes:
    """
    Chiffre un mot de passe en clair (string) en utilisant Cloud KMS.
    Retourne le texte chiffré sous forme de bytes.
    """
    if not isinstance(plaintext, str) or not plaintext:
        raise TypeError("Le mot de passe à chiffrer doit être une chaîne de caractères non vide.")

    try:
        # Conversion du string en bytes, requis par l'API
        plaintext_bytes = plaintext.encode("utf-8")
        
        # Appel à l'API KMS pour chiffrer
        response = kms_client.encrypt(name=KEY_NAME, plaintext=plaintext_bytes)
        
        return response.ciphertext
    except google_exceptions.PermissionDenied as e:
        st.error("Permission refusée pour chiffrer avec KMS. Vérifiez les droits IAM.")
        raise
    except Exception as e:
        print(f"Erreur inattendue lors du chiffrement KMS: {e}")
        raise


def decrypt_password(ciphertext: bytes) -> str:
    """
    Déchiffre un mot de passe (bytes) en utilisant Cloud KMS.
    Retourne le mot de passe en clair (string).
    """
    if not isinstance(ciphertext, bytes):
        raise TypeError("Le texte chiffré doit être de type bytes.")

    try:
        # Appel à l'API KMS pour déchiffrer
        response = kms_client.decrypt(name=KEY_NAME, ciphertext=ciphertext)

        # Conversion des bytes déchiffrés en string
        return response.plaintext.decode("utf-8")
    except google_exceptions.PermissionDenied as e:
        st.error("Permission refusée pour déchiffrer avec KMS. Vérifiez les droits IAM.")
        raise
    except Exception as e:
        print(f"Erreur inattendue lors du déchiffrement KMS: {e}")
        raise