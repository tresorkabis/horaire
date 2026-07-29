"""
Middleware personnalisé pour l'application Horaires ESFORCA.

RoleRefreshMiddleware
    Force le rafraîchissement du cache de rôles à chaque requête
    afin d'éviter que les changements de rôle ne restent obsolètes
    pendant une session utilisateur.
"""

from django.utils.deprecation import MiddlewareMixin


class RoleRefreshMiddleware(MiddlewareMixin):
    """Invalidate le cache ``_roles_cache`` du modèle Utilisateur à chaque requête."""

    def process_request(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            # Supprimer le cache des rôles s'il existe afin de forcer un
            # re-lecture depuis la base de données à chaque requête.
            if hasattr(user, "_roles_cache"):
                delattr(user, "_roles_cache")
