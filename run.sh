#!/bin/bash
# Script pour lancer l'application Django Horaires

# Vérifier si on est dans le bon répertoire
cd "$(dirname "$0")"

# Activer l'environnement virtuel
source venv/bin/activate

# Réinitialiser la base de données, régénérer les migrations,
# les appliquer et peupler la base avec les données de démonstration
python seed_data.py

# Lancer le serveur de développement
python manage.py runserver 0.0.0.0:8000
