# Fichier: Dockerfile
FROM python:3.11-slim

# Ajout de libpq-dev pour le pilote psycopg2
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# On remet la commande de démarrage de Streamlit
CMD exec python -m streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false