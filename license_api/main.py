# license_api/main.py

import os
import functions_framework
from google.cloud import firestore

db = firestore.Client()

@functions_framework.http
def verify_license(request):
    """Vérifie si une clé de licence correspond à un abonnement actif."""
    # On autorise les requêtes cross-origin (CORS) pour que la fonction du client puisse l'appeler
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # Gérer la requête pre-flight CORS
    if request.method == 'OPTIONS':
        return '', 204, headers

    request_json = request.get_json(silent=True)
    if not request_json or 'license_key' not in request_json:
        return ({"status": "error", "message": "Clé de licence manquante."}, 400, headers)

    license_key = request_json['license_key']

    # On cherche dans toutes les sous-collections 'subscriptions' du projet
    subs_ref = db.collection_group('subscriptions').where('license_key', '==', license_key).limit(1).stream()
    
    subscription = next(subs_ref, None)

    if not subscription:
        return ({"status": "inactive", "message": "Clé de licence invalide."}, 200, headers)

    sub_data = subscription.to_dict()
    if sub_data.get('status') in ('active', 'trialing'):
        return ({"status": "active"}, 200, headers)
    else:
        message = f"Abonnement non actif (statut: {sub_data.get('status')})."
        return ({"status": "inactive", "message": message}, 200, headers)

    return ({"status": "error", "message": "Erreur interne."}, 500, headers)