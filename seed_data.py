import os
import shutil
import subprocess
import sys
import django
import datetime

# ---------------------------------------------------------------------------
# Étape 0 : Nettoyage complet de la base de données et des migrations
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")
MIGRATIONS_DIR = os.path.join(BASE_DIR, "apps", "core", "migrations")


def reset_database():
    """Supprime la base de données SQLite si elle existe."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✅ Base de données supprimée : {DB_PATH}")
    else:
        print("ℹ️  Aucune base de données à supprimer.")


def reset_migrations():
    """Supprime tous les fichiers de migration sauf __init__.py."""
    if not os.path.isdir(MIGRATIONS_DIR):
        print(f"⚠️  Dossier de migrations introuvable : {MIGRATIONS_DIR}")
        return

    removed = 0
    for filename in os.listdir(MIGRATIONS_DIR):
        if filename == "__init__.py":
            continue
        filepath = os.path.join(MIGRATIONS_DIR, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
            removed += 1
    print(f"✅ {removed} fichier(s) de migration supprimé(s).")


def run_command(cmd, description):
    """Exécute une commande shell et affiche le résultat."""
    print(f"\n▶ {description}...")
    result = subprocess.run(cmd, shell=True, cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Erreur lors de {description} :")
        print(result.stderr)
        sys.exit(1)
    if result.stdout.strip():
        print(result.stdout.strip())
    print(f"✅ {description} terminé.")
    return result


def regenerate_and_apply_migrations():
    """Régénère les migrations et les applique."""
    run_command(
        f"{sys.executable} manage.py makemigrations core",
        "Régénération des migrations",
    )
    run_command(
        f"{sys.executable} manage.py migrate",
        "Application des migrations",
    )


# ---------------------------------------------------------------------------
# Peuplement de la base de données
# ---------------------------------------------------------------------------

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.models import (
    Utilisateur, Personnel, Etudiant, Role, Filiere,
    Promotion, Cours, Fonction, Creneau_Horaire, Horaire,
    Utilisateur_Role,
    STATUS_DRAFT, STATUS_PROPOSED, STATUS_CONFIRMED, STATUS_PUBLISHED,
    TYPE_COURS, TYPE_EXAMEN,
)


def seed():
    print("\n" + "=" * 60)
    print("Début du peuplement de la base de données ChronoPlan...")
    print("=" * 60)

    roles_names = ['Chef de Filière', 'Enseignant', 'Étudiant', 'SG-A']
    roles = {name: Role.objects.get_or_create(libelle=name)[0] for name in roles_names}

    gl, _ = Filiere.objects.get_or_create(nom_filiere="Génie Logiciel")
    sc, _ = Filiere.objects.get_or_create(nom_filiere="Sciences Commerciales")
    rt, _ = Filiere.objects.get_or_create(nom_filiere="Réseaux et Techniques de Maintenance")
    sd, _ = Filiere.objects.get_or_create(nom_filiere="Secrétariat de Direction")

    # 3 promotions pour Génie Logiciel : L1, L2, L3
    l1_gl, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=gl)
    l2_gl, _ = Promotion.objects.get_or_create(designation="L2", annee_academique="2025-2026", filiere=gl)
    l3_gl, _ = Promotion.objects.get_or_create(designation="L3", annee_academique="2025-2026", filiere=gl)
    l1_sc, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=sc)
    l1_rt, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=rt)
    l1_sd, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=sd)

    def create_actor(identifiant, nom, pnom, role_name, model_class, **extra):
        user = model_class.objects.filter(email=identifiant).first()
        if not user:
            user = model_class.objects.create_user(
                email=identifiant, nom=nom, post_nom=pnom, sexe='M',
                password='demo'
            )
        for field, value in extra.items():
            setattr(user, field, value)
        user.save()
        Utilisateur_Role.objects.get_or_create(id_util=user, role=roles[role_name])
        return user

    # Nettoyer les anciennes fonctions qui ne sont plus pertinentes
    Fonction.objects.filter(intitule__in=["Cours Théorique", "Travaux Pratiques", "Examen"]).delete()

    f_chef, _ = Fonction.objects.get_or_create(intitule="Chef de Filière")
    f_enseignant, _ = Fonction.objects.get_or_create(intitule="Enseignant")
    f_sga, _ = Fonction.objects.get_or_create(intitule="SG-A")

    chef = create_actor("chef", "MUKENDI", "Alain", "Chef de Filière", Personnel, matricule="P001", grade="Professeur", fonction=f_chef)
    prof = create_actor("prof", "TSHIMANGA", "Jean", "Enseignant", Personnel, matricule="P002", grade="Chef de Travaux", fonction=f_enseignant)
    sga = create_actor("sga", "KASSONGO", "Bibiche", "SG-A", Personnel, matricule="P003", grade="Secrétaire Général", fonction=f_sga)
    sga.is_staff = True
    sga.is_superuser = True
    sga.save()
    etud = create_actor("etud", "LUMUMBA", "Patrice", "Étudiant", Etudiant, num_matric="S001", date_naiss=datetime.date(2003, 1, 1), promotion=l1_gl)

    # Ajouter des comptes supplémentaires pour les tests
    chef2 = create_actor("chef2", "KABEYA", "Pierre", "Chef de Filière", Personnel, matricule="P004", grade="Professeur", fonction=f_chef)
    prof2 = create_actor("prof2", "MULUMBA", "Paul", "Enseignant", Personnel, matricule="P005", grade="Chef de Travaux", fonction=f_enseignant)
    etud2 = create_actor("etud2", "KABILA", "Joseph", "Étudiant", Etudiant, num_matric="S002", date_naiss=datetime.date(2002, 5, 15), promotion=l1_gl)
    etud3 = create_actor("etud3", "MOBUTU", "Marie", "Étudiant", Etudiant, num_matric="S003", date_naiss=datetime.date(2003, 3, 10), promotion=l2_gl)
    chef3 = create_actor("chef3", "KASONGO", "Luc", "Chef de Filière", Personnel, matricule="P006", grade="Professeur", fonction=f_chef)
    prof3 = create_actor("prof3", "MULOPWE", "Sophie", "Enseignant", Personnel, matricule="P007", grade="Chef de Travaux", fonction=f_enseignant)

    # 6 cours pour Génie Logiciel (3 par semestre)
    c1, _ = Cours.objects.get_or_create(titre="Algorithmique Avancée", defaults={'duree': 120, 'promotion': l1_gl})
    c2, _ = Cours.objects.get_or_create(titre="Base de Données NoSQL", defaults={'duree': 90, 'promotion': l1_gl})
    c3, _ = Cours.objects.get_or_create(titre="Architecture des Ordinateurs", defaults={'duree': 120, 'promotion': l2_gl})
    c7, _ = Cours.objects.get_or_create(titre="Programmation Web Avancée", defaults={'duree': 120, 'promotion': l1_gl})
    c8, _ = Cours.objects.get_or_create(titre="Intelligence Artificielle", defaults={'duree': 90, 'promotion': l2_gl})
    c9, _ = Cours.objects.get_or_create(titre="Sécurité Informatique", defaults={'duree': 120, 'promotion': l3_gl})
    # Cours pour autres filières
    c4, _ = Cours.objects.get_or_create(titre="Marketing Digital", defaults={'duree': 90, 'promotion': l1_sc})
    c5, _ = Cours.objects.get_or_create(titre="Administration Réseau", defaults={'duree': 120, 'promotion': l1_rt})
    c6, _ = Cours.objects.get_or_create(titre="Communication Professionnelle", defaults={'duree': 90, 'promotion': l1_sd})

    # Associer l'enseignant à chaque cours
    c1.enseignant = chef
    c1.save()
    c2.enseignant = prof
    c2.save()
    c3.enseignant = prof
    c3.save()
    c7.enseignant = chef
    c7.save()
    c8.enseignant = prof
    c8.save()
    c9.enseignant = prof
    c9.save()
    c4.enseignant = prof
    c4.save()
    c5.enseignant = chef
    c5.save()
    c6.enseignant = prof
    c6.save()

    # ------------------------------------------------------------------
    # Création des horaires globaux
    # ------------------------------------------------------------------

    # Chaque promotion a exactement 2 horaires de cours : Semestre 1 et Semestre 2
    h_l1_s1, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Semestre 1 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_COURS})
    h_l1_s2, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Semestre 2 - 2026", defaults={'status': STATUS_PROPOSED, 'type_horaire': TYPE_COURS})
    h_l2_s1, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Semestre 1 - 2026", defaults={'status': STATUS_CONFIRMED, 'type_horaire': TYPE_COURS})
    h_l2_s2, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Semestre 2 - 2026", defaults={'status': STATUS_CONFIRMED, 'type_horaire': TYPE_COURS})
    h_l3_s1, _ = Horaire.objects.get_or_create(promotion=l3_gl, titre="Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_l3_s2, _ = Horaire.objects.get_or_create(promotion=l3_gl, titre="Semestre 2 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_sc_s1, _ = Horaire.objects.get_or_create(promotion=l1_sc, titre="Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_sc_s2, _ = Horaire.objects.get_or_create(promotion=l1_sc, titre="Semestre 2 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_rt_s1, _ = Horaire.objects.get_or_create(promotion=l1_rt, titre="Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_rt_s2, _ = Horaire.objects.get_or_create(promotion=l1_rt, titre="Semestre 2 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_sd_s1, _ = Horaire.objects.get_or_create(promotion=l1_sd, titre="Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_sd_s2, _ = Horaire.objects.get_or_create(promotion=l1_sd, titre="Semestre 2 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})

    # Chaque promotion a 4 horaires d'examens : session S1, rattrapage S1, session S2, rattrapage S2
    h_gl_s1_session, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Session Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_gl_s1_rattrapage, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Rattrapage Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_gl_s2_session, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Session Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})
    h_gl_s2_rattrapage, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Rattrapage Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})

    h_l2_s1_session, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Session Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_l2_s1_rattrapage, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Rattrapage Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_l2_s2_session, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Session Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})
    h_l2_s2_rattrapage, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Rattrapage Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})

    h_l3_s1_session, _ = Horaire.objects.get_or_create(promotion=l3_gl, titre="Session Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_l3_s1_rattrapage, _ = Horaire.objects.get_or_create(promotion=l3_gl, titre="Rattrapage Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_l3_s2_session, _ = Horaire.objects.get_or_create(promotion=l3_gl, titre="Session Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})
    h_l3_s2_rattrapage, _ = Horaire.objects.get_or_create(promotion=l3_gl, titre="Rattrapage Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})

    h_sc_s1_session, _ = Horaire.objects.get_or_create(promotion=l1_sc, titre="Session Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_sc_s1_rattrapage, _ = Horaire.objects.get_or_create(promotion=l1_sc, titre="Rattrapage Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_sc_s2_session, _ = Horaire.objects.get_or_create(promotion=l1_sc, titre="Session Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})
    h_sc_s2_rattrapage, _ = Horaire.objects.get_or_create(promotion=l1_sc, titre="Rattrapage Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})

    h_rt_s1_session, _ = Horaire.objects.get_or_create(promotion=l1_rt, titre="Session Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_rt_s1_rattrapage, _ = Horaire.objects.get_or_create(promotion=l1_rt, titre="Rattrapage Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_rt_s2_session, _ = Horaire.objects.get_or_create(promotion=l1_rt, titre="Session Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})
    h_rt_s2_rattrapage, _ = Horaire.objects.get_or_create(promotion=l1_rt, titre="Rattrapage Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})

    h_sd_s1_session, _ = Horaire.objects.get_or_create(promotion=l1_sd, titre="Session Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_sd_s1_rattrapage, _ = Horaire.objects.get_or_create(promotion=l1_sd, titre="Rattrapage Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_sd_s2_session, _ = Horaire.objects.get_or_create(promotion=l1_sd, titre="Session Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})
    h_sd_s2_rattrapage, _ = Horaire.objects.get_or_create(promotion=l1_sd, titre="Rattrapage Semestre 2 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})

    # ------------------------------------------------------------------
    # Création des créneaux
    # ------------------------------------------------------------------

    Creneau_Horaire.objects.all().delete()

    # --- Horaires de cours ---

    # L1 GL - Semestre 1 (DRAFT) : 2 créneaux
    Creneau_Horaire.objects.get_or_create(jours="Lundi", heure="08:00:00", cours=c1, personnel=chef, horaire=h_l1_s1, status=STATUS_DRAFT)
    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="08:00:00", cours=c7, personnel=chef, horaire=h_l1_s1, status=STATUS_DRAFT)

    # L1 GL - Semestre 2 (PROPOSED) : 2 créneaux
    Creneau_Horaire.objects.get_or_create(jours="Mardi", heure="11:40:00", cours=c2, personnel=prof, horaire=h_l1_s2, status=STATUS_PROPOSED)
    Creneau_Horaire.objects.get_or_create(jours="Vendredi", heure="11:40:00", cours=c8, personnel=prof, horaire=h_l1_s2, status=STATUS_PROPOSED)

    # L2 GL - Semestre 1 (CONFIRMED) : 2 créneaux
    Creneau_Horaire.objects.get_or_create(jours="Jeudi", heure="11:40:00", cours=c3, personnel=prof, horaire=h_l2_s1, status=STATUS_CONFIRMED)
    Creneau_Horaire.objects.get_or_create(jours="Samedi", heure="08:00:00", cours=c9, personnel=prof, horaire=h_l2_s1, status=STATUS_CONFIRMED)

    # L2 GL - Semestre 2 (CONFIRMED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(jours="Vendredi", heure="08:00:00", cours=c3, personnel=prof, horaire=h_l2_s2, status=STATUS_CONFIRMED)

    # L3 GL - Semestre 1 (PUBLISHED) : 3 créneaux
    Creneau_Horaire.objects.get_or_create(jours="Lundi", heure="11:40:00", cours=c7, personnel=chef, horaire=h_l3_s1, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Samedi", heure="11:40:00", cours=c8, personnel=prof3, horaire=h_l3_s1, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Jeudi", heure="08:00:00", cours=c9, personnel=prof3, horaire=h_l3_s1, status=STATUS_PUBLISHED)

    # L3 GL - Semestre 2 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(jours="Mardi", heure="08:00:00", cours=c7, personnel=chef, horaire=h_l3_s2, status=STATUS_PUBLISHED)

    # Sciences Commerciales - Semestre 1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(jours="Lundi", heure="11:40:00", cours=c4, personnel=prof2, horaire=h_sc_s1, status=STATUS_PUBLISHED)

    # Sciences Commerciales - Semestre 2 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="08:00:00", cours=c4, personnel=prof2, horaire=h_sc_s2, status=STATUS_PUBLISHED)

    # Réseaux - Semestre 1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(jours="Mardi", heure="08:00:00", cours=c5, personnel=chef2, horaire=h_rt_s1, status=STATUS_PUBLISHED)

    # Réseaux - Semestre 2 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(jours="Jeudi", heure="08:00:00", cours=c5, personnel=chef2, horaire=h_rt_s2, status=STATUS_PUBLISHED)

    # Secrétariat - Semestre 1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="11:40:00", cours=c6, personnel=prof2, horaire=h_sd_s1, status=STATUS_PUBLISHED)

    # Secrétariat - Semestre 2 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(jours="Vendredi", heure="08:00:00", cours=c6, personnel=prof2, horaire=h_sd_s2, status=STATUS_PUBLISHED)

    # --- Horaires d'examens ---

    # L1 GL - Session S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 15), heure="11:40:00", cours=c1, 
        personnel=chef3, horaire=h_gl_s1_session, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # L1 GL - Rattrapage S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 22), heure="08:00:00", cours=c2, 
        personnel=prof3, horaire=h_gl_s1_rattrapage, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # L2 GL - Session S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 16), heure="08:00:00", cours=c3, 
        personnel=prof3, horaire=h_l2_s1_session, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # L2 GL - Rattrapage S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 23), heure="11:40:00", cours=c8, 
        personnel=prof3, horaire=h_l2_s1_rattrapage, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # L3 GL - Session S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 17), heure="11:40:00", cours=c9, 
        personnel=chef3, horaire=h_l3_s1_session, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # L3 GL - Rattrapage S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 24), heure="08:00:00", cours=c7, 
        personnel=chef3, horaire=h_l3_s1_rattrapage, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # SC - Session S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 18), heure="08:00:00", cours=c4, 
        personnel=prof2, horaire=h_sc_s1_session, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # SC - Rattrapage S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 25), heure="08:00:00", cours=c4, 
        personnel=prof2, horaire=h_sc_s1_rattrapage, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # Réseaux - Session S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 19), heure="11:40:00", cours=c5, 
        personnel=chef2, horaire=h_rt_s1_session, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # Réseaux - Rattrapage S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 26), heure="08:00:00", cours=c5, 
        personnel=chef2, horaire=h_rt_s1_rattrapage, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # Secrétariat - Session S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 20), heure="08:00:00", cours=c6, 
        personnel=prof2, horaire=h_sd_s1_session, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # Secrétariat - Rattrapage S1 (PUBLISHED) : 1 créneau
    Creneau_Horaire.objects.get_or_create(
        date=datetime.date(2026, 6, 27), heure="11:40:00", cours=c6, 
        personnel=prof2, horaire=h_sd_s1_rattrapage, status=STATUS_PUBLISHED, type_horaire=TYPE_EXAMEN
    )

    # --- Proposition isolée (sans horaire) ---
    Creneau_Horaire.objects.get_or_create(jours="Mardi", heure="08:00:00", cours=c2, personnel=prof, horaire=None, status=STATUS_PROPOSED, annotations="Proposition pour le créneau de Base de Données NoSQL")

    # ------------------------------------------------------------------
    # Vérification finale : aucun horaire non-DRAFT ne doit être vide
    # ------------------------------------------------------------------

    horaires_non_draft = Horaire.objects.exclude(status=STATUS_DRAFT)
    horaires_vides = [h for h in horaires_non_draft if not h.creneaux.exists()]
    if horaires_vides:
        print("\n⚠️  ATTENTION : Des horaires non-DRAFT sont vides :")
        for h in horaires_vides:
            print(f"  - {h.titre} ({h.promotion}) — statut : {h.status}")
        print("Le seed est incohérent avec la règle métier.")
    else:
        print("\n✅ Vérification : tous les horaires non-DRAFT ont au moins un créneau.")

    print("\n" + "=" * 60)
    print("Base de données prête !")
    print("=" * 60)
    print("Utilisateurs de test :")
    print("1. Chef Filière 1 : chef / demo")
    print("2. Chef Filière 2 : chef2 / demo")
    print("3. Chef Filière 3 : chef3 / demo")
    print("4. Enseignant 1   : prof / demo")
    print("5. Enseignant 2   : prof2 / demo")
    print("6. Enseignant 3   : prof3 / demo")
    print("7. SGA           : sga / demo")
    print("8. Étudiant 1    : etud / demo")
    print("9. Étudiant 2    : etud2 / demo")
    print("10. Étudiant 3   : etud3 / demo")
    print("-" * 60)
    print(f"Horaires de cours  : {Horaire.objects.filter(type_horaire=TYPE_COURS).count()}")
    print(f"Horaires d'examens : {Horaire.objects.filter(type_horaire=TYPE_EXAMEN).count()}")
    print(f"Créneaux créés     : {Creneau_Horaire.objects.count()}")
    print(f"Propositions isolées (sans horaire) : {Creneau_Horaire.objects.filter(horaire__isnull=True).count()}")


if __name__ == "__main__":
    print("=" * 60)
    print("ChronoPlan — Réinitialisation complète de la base de données")
    print("=" * 60)

    # 1. Supprimer la base de données
    reset_database()

    # 2. Supprimer les migrations
    reset_migrations()

    # 3. Régénérer et appliquer les migrations
    regenerate_and_apply_migrations()

    # 4. Peupler la base de données
    seed()