# Fichier : Dockerfile

# Utilise une image Python 3.11 officielle comme base
FROM python:3.11-slim

# Définit le répertoire de travail dans le conteneur
WORKDIR /app

# Copie le fichier des dépendances et les installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le reste du code de votre application
COPY . .

# ### MODIFIÉ ### : Commande de démarrage plus robuste
CMD exec python -m streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false