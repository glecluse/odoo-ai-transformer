import os
from google.cloud import kms

# Récupération des variables d'environnement
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION_ID = "europe-west1"
KEY_RING_ID = "odoo-app-keyring"
KEY_ID = "odoo-password-key"

# Construction du nom de la ressource de la clé
KEY_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION_ID}/keyRings/{KEY_RING_ID}/cryptoKeys/{KEY_ID}"

# Initialisation du client KMS
kms_client = kms.KeyManagementServiceClient()

def encrypt_password(plaintext: str) -> bytes:
    """Chiffre un mot de passe en utilisant Cloud KMS."""
    plaintext_bytes = plaintext.encode("utf-8")
    response = kms_client.encrypt(name=KEY_NAME, plaintext=plaintext_bytes)
    return response.ciphertext

def decrypt_password(ciphertext: bytes) -> str:
    """Déchiffre un mot de passe en utilisant Cloud KMS."""
    response = kms_client.decrypt(name=KEY_NAME, ciphertext=ciphertext)
    return response.plaintext.decode("utf-8")