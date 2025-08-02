FROM python:3.11-slim

# Empêche l'erreur "externally-managed-environment"
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Crée le dossier de l'application
WORKDIR /app

# Copie les fichiers de l'application
COPY . .

# Installe les dépendances
RUN pip install --upgrade pip && pip install -r requirements.txt

# Port utilisé par Streamlit
EXPOSE 8080

# Lance l'application Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
