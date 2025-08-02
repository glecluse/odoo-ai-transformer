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

# Commande pour démarrer l'application lorsque le conteneur démarre
# Cette version est la plus robuste pour interpréter les variables d'environnement
CMD ["sh", "-c", "streamlit run app.py --server.port=$PORT"]