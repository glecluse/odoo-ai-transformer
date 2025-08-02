# Utiliser une image Python officielle comme base
FROM python:3.10-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier des dépendances
COPY requirements.txt requirements.txt

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code de l'application dans le conteneur
COPY . .

# Exposer le port sur lequel Streamlit s'exécute par défaut
EXPOSE 8501

# Commande pour démarrer l'application lorsque le conteneur démarre
# healthz est un endpoint de santé que Cloud Run peut utiliser
CMD ["sh", "-c", "streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false"]