#!/bin/bash

# Script de lancement de l'application Django

echo "Démarrage de l'application..."

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "Installation des dépendances..."
pip install -r requirements.txt

# Appliquer les migrations
echo "Application des migrations..."
python manage.py migrate

# Lancer le serveur
echo "Lancement du serveur de développement..."
python manage.py runserver 0.0.0.0:8000