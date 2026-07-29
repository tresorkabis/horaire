"""
Context processors pour l'application Horaires ESFORCA.

Le context processor ``roles_uml`` expose les drapeaux de rôle
(``is_chef``, ``is_enseignant``, etc.) a tous les templates.
Il s'appuie sur le ``cached_property`` du modèle Utilisateur
afin d'eviter les requetes redondantes.
"""

from .models import ROLE_CHEF, ROLE_ENSEIGNANT, ROLE_ETUDIANT, ROLE_SGA


def roles_uml(request):
    """Injecte les informations de role dans le contexte de tous les templates."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    roles = user.roles  # Utilise le cached_property du modèle
    return {
        "user_roles": roles,
        "is_chef": ROLE_CHEF in roles,
        "is_enseignant": ROLE_ENSEIGNANT in roles,
        "is_etudiant": ROLE_ETUDIANT in roles,
        "is_sga": ROLE_SGA in roles,
    }
