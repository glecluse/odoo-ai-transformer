# On repart de la version de Python que vous utilisiez et qui est validée
FROM python:3.10-slim

# On définit le répertoire de travail
WORKDIR /app

# On ajoute la ligne qui installe les outils de compilation (la cause probable de l'échec du build)
# On ajoute aussi une commande pour nettoyer le cache et garder l'image légère
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# On copie et on installe les dépendances Python
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# On copie le reste du code de l'application
COPY . .

# On utilise votre commande de démarrage qui est la bonne pour Cloud Run
CMD ["sh", "-c", "streamlit run app.py --server.port=$PORT"]