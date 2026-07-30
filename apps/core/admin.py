from django.contrib import admin

from .models import (
    Cours,
    Creneau_Horaire,
    Disponibilite,
    Etudiant,
    Filiere,
    Fonction,
    Personnel,
    Promotion,
    Role,
    Utilisateur,
    Utilisateur_Role,
)


# ---------------------------------------------------------------------------
# Utilisateur & rôles
# ---------------------------------------------------------------------------

@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ("id_user", "nom", "post_nom", "email", "sexe", "is_active", "is_staff", "is_superuser")
    list_filter = ("sexe", "is_active", "is_staff", "is_superuser")
    search_fields = ("nom", "post_nom", "email")
    ordering = ("nom", "post_nom")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id_role", "libelle")
    search_fields = ("libelle",)
    ordering = ("libelle",)


@admin.register(Utilisateur_Role)
class UtilisateurRoleAdmin(admin.ModelAdmin):
    list_display = ("id_util", "role", "date")
    list_filter = ("role", "date")
    search_fields = ("id_util__nom", "id_util__post_nom", "role__libelle")
    date_hierarchy = "date"


# ---------------------------------------------------------------------------
# Personnel & étudiants
# ---------------------------------------------------------------------------

@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ("id_user", "nom", "post_nom", "email", "matricule", "grade", "is_active")
    list_filter = ("grade", "is_active")
    search_fields = ("nom", "post_nom", "email", "matricule")
    ordering = ("nom", "post_nom")


@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = ("id_user", "nom", "post_nom", "email", "num_matric", "promotion")
    list_filter = ("promotion__filiere", "promotion")
    search_fields = ("nom", "post_nom", "email", "num_matric")
    autocomplete_fields = ("promotion",)
    ordering = ("nom", "post_nom")


# ---------------------------------------------------------------------------
# Structure académique
# ---------------------------------------------------------------------------

@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ("id_filiere", "nom_filiere")
    search_fields = ("nom_filiere",)
    ordering = ("nom_filiere",)


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("id_prom", "designation", "annee_academique", "filiere")
    list_filter = ("filiere", "annee_academique")
    search_fields = ("designation", "annee_academique")
    autocomplete_fields = ("filiere",)
    ordering = ("-annee_academique", "designation")


@admin.register(Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ("id_cours", "titre", "duree")
    search_fields = ("titre",)
    ordering = ("titre",)


@admin.register(Fonction)
class FonctionAdmin(admin.ModelAdmin):
    list_display = ("id_fonction", "intitule")
    search_fields = ("intitule",)
    ordering = ("intitule",)


# ---------------------------------------------------------------------------
# Planification
# ---------------------------------------------------------------------------

@admin.register(Creneau_Horaire)
class CreneauHoraireAdmin(admin.ModelAdmin):
    list_display = ("id_chrono", "jours", "heure", "cours", "personnel", "fonction", "status")
    list_filter = ("jours", "status", "fonction", "cours")
    search_fields = ("cours__titre", "personnel__nom", "personnel__post_nom")
    autocomplete_fields = ("cours", "personnel", "fonction")
    ordering = ("jours", "heure")


@admin.register(Disponibilite)
class DisponibiliteAdmin(admin.ModelAdmin):
    list_display = ("enseignant", "jour", "heure_debut", "heure_fin", "note")
    list_filter = ("jour", "enseignant")
    search_fields = ("enseignant__nom", "enseignant__post_nom")
    autocomplete_fields = ("enseignant",)
    ordering = ("enseignant", "jour", "heure_debut")
