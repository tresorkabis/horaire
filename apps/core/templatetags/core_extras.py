from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Retourne la valeur d'un dictionnaire pour une clé donnée."""
    return dictionary.get(key)