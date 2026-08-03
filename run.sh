#!/bin/bash
# Script pour lancer l'application Django Horaires

# Vérifier si on est dans le bon répertoire
cd "$(dirname "$0")"

# Activer l'environnement virtuel
source venv/bin/activate

# Appliquer les migrations
python manage.py migrate

# Créer les données de démonstration si nécessaire
python seed_data.py

# Lancer le serveur de développement
python manage.py runserver 0.0.0.0:8000