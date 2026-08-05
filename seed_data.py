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
    Disponibilite, Utilisateur_Role,
    STATUS_DRAFT, STATUS_PROPOSED, STATUS_CONFIRMED, STATUS_PUBLISHED,
    TYPE_COURS, TYPE_EXAMEN,
)


def seed():
    print("\n" + "=" * 60)
    print("Début du peuplement de la base de données Horaires ESFORCA...")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Rôles
    # ------------------------------------------------------------------
    roles_names = ['Chef de Filière', 'Enseignant', 'Étudiant', 'SG-A']
    roles = {name: Role.objects.get_or_create(libelle=name)[0] for name in roles_names}

    # ------------------------------------------------------------------
    # 2. Filières
    # ------------------------------------------------------------------
    gl, _ = Filiere.objects.get_or_create(nom_filiere="Génie Logiciel")
    sc, _ = Filiere.objects.get_or_create(nom_filiere="Sciences Commerciales")
    rt, _ = Filiere.objects.get_or_create(nom_filiere="Réseaux et Techniques de Maintenance")
    sd, _ = Filiere.objects.get_or_create(nom_filiere="Secrétariat de Direction")

    # ------------------------------------------------------------------
    # 3. Promotions (2025-2026)
    # ------------------------------------------------------------------
    l1_gl, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=gl)
    l2_gl, _ = Promotion.objects.get_or_create(designation="L2", annee_academique="2025-2026", filiere=gl)
    l3_gl, _ = Promotion.objects.get_or_create(designation="L3", annee_academique="2025-2026", filiere=gl)
    l1_sc, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=sc)
    l2_sc, _ = Promotion.objects.get_or_create(designation="L2", annee_academique="2025-2026", filiere=sc)
    l1_rt, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=rt)
    l2_rt, _ = Promotion.objects.get_or_create(designation="L2", annee_academique="2025-2026", filiere=rt)
    l1_sd, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=sd)
    l2_sd, _ = Promotion.objects.get_or_create(designation="L2", annee_academique="2025-2026", filiere=sd)

    # ------------------------------------------------------------------
    # 4. Fonctions
    # ------------------------------------------------------------------
    Fonction.objects.filter(intitule__in=["Cours Théorique", "Travaux Pratiques", "Examen"]).delete()
    f_chef, _ = Fonction.objects.get_or_create(intitule="Chef de Filière")
    f_enseignant, _ = Fonction.objects.get_or_create(intitule="Enseignant")
    f_sga, _ = Fonction.objects.get_or_create(intitule="SG-A")

    # ------------------------------------------------------------------
    # 5. Utilisateurs (Personnel & Étudiants)
    # ------------------------------------------------------------------
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

    # Chef de Génie Logiciel
    chef_gl = create_actor("chef", "MUKENDI", "Alain", "Chef de Filière", Personnel,
                           matricule="P001", grade="Professeur", fonction=f_chef, filiere=gl)
    # Enseignants Génie Logiciel
    prof_gl1 = create_actor("prof", "TSHIMANGA", "Jean", "Enseignant", Personnel,
                            matricule="P002", grade="Chef de Travaux", fonction=f_enseignant)
    prof_gl2 = create_actor("prof2", "MULUMBA", "Paul", "Enseignant", Personnel,
                            matricule="P005", grade="Chef de Travaux", fonction=f_enseignant)
    prof_gl3 = create_actor("prof3", "MULOPWE", "Sophie", "Enseignant", Personnel,
                            matricule="P007", grade="Assistant", fonction=f_enseignant)

    # Chef de Sciences Commerciales
    chef_sc = create_actor("chef2", "KABEYA", "Pierre", "Chef de Filière", Personnel,
                           matricule="P004", grade="Professeur", fonction=f_chef, filiere=sc)
    prof_sc = create_actor("prof_sc", "KASONGO", "Marie", "Enseignant", Personnel,
                           matricule="P008", grade="Chef de Travaux", fonction=f_enseignant)

    # Chef de Réseaux
    chef_rt = create_actor("chef3", "KASONGO", "Luc", "Chef de Filière", Personnel,
                           matricule="P006", grade="Professeur", fonction=f_chef, filiere=rt)
    prof_rt = create_actor("prof_rt", "ILUNGA", "Joseph", "Enseignant", Personnel,
                           matricule="P009", grade="Assistant", fonction=f_enseignant)

    # Chef de Secrétariat
    chef_sd = create_actor("chef_sd", "NZUZI", "Béatrice", "Chef de Filière", Personnel,
                           matricule="P010", grade="Professeur", fonction=f_chef, filiere=sd)
    prof_sd = create_actor("prof_sd", "MUKENDI", "Esther", "Enseignant", Personnel,
                           matricule="P011", grade="Chef de Travaux", fonction=f_enseignant)

    # SG-A
    sga = create_actor("sga", "KASSONGO", "Bibiche", "SG-A", Personnel,
                       matricule="P003", grade="Secrétaire Général", fonction=f_sga)
    sga.is_staff = True
    sga.is_superuser = True
    sga.save()

    # Étudiants
    etud1 = create_actor("etud", "LUMUMBA", "Patrice", "Étudiant", Etudiant,
                         num_matric="S001", date_naiss=datetime.date(2003, 1, 1), promotion=l1_gl)
    etud2 = create_actor("etud2", "KABILA", "Joseph", "Étudiant", Etudiant,
                         num_matric="S002", date_naiss=datetime.date(2002, 5, 15), promotion=l1_gl)
    etud3 = create_actor("etud3", "MOBUTU", "Marie", "Étudiant", Etudiant,
                         num_matric="S003", date_naiss=datetime.date(2003, 3, 10), promotion=l2_gl)
    etud4 = create_actor("etud4", "TSHOMBE", "Albert", "Étudiant", Etudiant,
                         num_matric="S004", date_naiss=datetime.date(2002, 8, 20), promotion=l3_gl)

    # ------------------------------------------------------------------
    # 6. Cours (durée en heures, assignés aux enseignants cohérents)
    # ------------------------------------------------------------------
    def create_cours(titre, duree, enseignant, promotion):
        cours, _ = Cours.objects.get_or_create(
            titre=titre,
            defaults={
                'duree': duree,
                'duree_unite': 'H',
                'enseignant': enseignant,
                'promotion': promotion,
            }
        )
        cours.enseignant = enseignant
        cours.promotion = promotion
        cours.save()
        return cours

    # Cours Génie Logiciel - L1
    c_gl1_1 = create_cours("Algorithmique Avancée", 30, prof_gl1, l1_gl)
    c_gl1_2 = create_cours("Base de Données NoSQL", 45, prof_gl2, l1_gl)
    c_gl1_3 = create_cours("Programmation Web Avancée", 30, prof_gl1, l1_gl)
    c_gl1_4 = create_cours("Mathématiques Discrètes", 45, prof_gl3, l1_gl)

    # Cours Génie Logiciel - L2
    c_gl2_1 = create_cours("Architecture des Ordinateurs", 30, prof_gl2, l2_gl)
    c_gl2_2 = create_cours("Intelligence Artificielle", 45, prof_gl3, l2_gl)
    c_gl2_3 = create_cours("Génie Logiciel", 30, prof_gl1, l2_gl)
    c_gl2_4 = create_cours("Systèmes d'Exploitation", 45, prof_gl2, l2_gl)

    # Cours Génie Logiciel - L3
    c_gl3_1 = create_cours("Sécurité Informatique", 30, prof_gl3, l3_gl)
    c_gl3_2 = create_cours("Réseaux Avancés", 45, prof_gl1, l3_gl)
    c_gl3_3 = create_cours("Cloud Computing", 30, prof_gl2, l3_gl)
    c_gl3_4 = create_cours("Big Data", 45, prof_gl3, l3_gl)

    # Cours Sciences Commerciales - L1
    c_sc1_1 = create_cours("Marketing Digital", 45, prof_sc, l1_sc)
    c_sc1_2 = create_cours("Comptabilité Générale", 30, chef_sc, l1_sc)

    # Cours Sciences Commerciales - L2
    c_sc2_1 = create_cours("Finance d'Entreprise", 45, prof_sc, l2_sc)
    c_sc2_2 = create_cours("Management Stratégique", 30, chef_sc, l2_sc)

    # Cours Réseaux - L1
    c_rt1_1 = create_cours("Administration Réseau", 30, prof_rt, l1_rt)
    c_rt1_2 = create_cours("Électronique Appliquée", 45, chef_rt, l1_rt)

    # Cours Réseaux - L2
    c_rt2_1 = create_cours("Maintenance Informatique", 30, prof_rt, l2_rt)
    c_rt2_2 = create_cours("Sécurité Réseau", 45, chef_rt, l2_rt)

    # Cours Secrétariat - L1
    c_sd1_1 = create_cours("Communication Professionnelle", 45, prof_sd, l1_sd)
    c_sd1_2 = create_cours("Bureautique Avancée", 30, chef_sd, l1_sd)

    # Cours Secrétariat - L2
    c_sd2_1 = create_cours("Gestion Administrative", 45, prof_sd, l2_sd)
    c_sd2_2 = create_cours("Secrétariat de Direction", 30, chef_sd, l2_sd)

    # ------------------------------------------------------------------
    # 7. Disponibilités des enseignants
    # ------------------------------------------------------------------
    Disponibilite.objects.all().delete()

    def create_dispo(enseignant, jour, heure, note=""):
        Disponibilite.objects.get_or_create(
            enseignant=enseignant, jour=jour, heure=heure,
            defaults={'note': note}
        )

    # Disponibilités prof_gl1 (TSHIMANGA Jean)
    for jour in ["Lundi", "Mardi", "Mercredi", "Vendredi"]:
        create_dispo(prof_gl1, jour, "08:00:00")
    for jour in ["Jeudi", "Samedi"]:
        create_dispo(prof_gl1, jour, "11:40:00")

    # Disponibilités prof_gl2 (MULUMBA Paul)
    for jour in ["Lundi", "Mercredi", "Vendredi"]:
        create_dispo(prof_gl2, jour, "11:40:00")
    for jour in ["Mardi", "Jeudi", "Samedi"]:
        create_dispo(prof_gl2, jour, "08:00:00")

    # Disponibilités prof_gl3 (MULOPWE Sophie)
    for jour in ["Mardi", "Jeudi", "Samedi"]:
        create_dispo(prof_gl3, jour, "08:00:00")
    for jour in ["Lundi", "Vendredi"]:
        create_dispo(prof_gl3, jour, "11:40:00")

    # Disponibilités chef_gl (MUKENDI Alain)
    for jour in ["Lundi", "Mercredi", "Samedi"]:
        create_dispo(chef_gl, jour, "08:00:00")

    # Disponibilités prof_sc
    for jour in ["Lundi", "Mardi", "Jeudi"]:
        create_dispo(prof_sc, jour, "08:00:00")

    # Disponibilités prof_rt
    for jour in ["Mardi", "Jeudi", "Vendredi"]:
        create_dispo(prof_rt, jour, "11:40:00")

    # Disponibilités prof_sd
    for jour in ["Lundi", "Mercredi", "Vendredi"]:
        create_dispo(prof_sd, jour, "11:40:00")

    # ------------------------------------------------------------------
    # 8. Horaires globaux (cours)
    # ------------------------------------------------------------------
    def create_horaire(promotion, titre, status, type_horaire=TYPE_COURS):
        horaire, _ = Horaire.objects.get_or_create(
            promotion=promotion, titre=titre,
            defaults={'status': status, 'type_horaire': type_horaire}
        )
        horaire.status = status
        horaire.type_horaire = type_horaire
        horaire.save()
        return horaire

    # Génie Logiciel
    h_l1_s1 = create_horaire(l1_gl, "Semestre 1 - 2025-2026", STATUS_DRAFT)
    h_l1_s2 = create_horaire(l1_gl, "Semestre 2 - 2025-2026", STATUS_PROPOSED)
    h_l2_s1 = create_horaire(l2_gl, "Semestre 1 - 2025-2026", STATUS_CONFIRMED)
    h_l2_s2 = create_horaire(l2_gl, "Semestre 2 - 2025-2026", STATUS_CONFIRMED)
    h_l3_s1 = create_horaire(l3_gl, "Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_l3_s2 = create_horaire(l3_gl, "Semestre 2 - 2025-2026", STATUS_PUBLISHED)

    # Sciences Commerciales
    h_sc_s1 = create_horaire(l1_sc, "Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_sc_s2 = create_horaire(l1_sc, "Semestre 2 - 2025-2026", STATUS_PUBLISHED)
    h_sc2_s1 = create_horaire(l2_sc, "Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_sc2_s2 = create_horaire(l2_sc, "Semestre 2 - 2025-2026", STATUS_PUBLISHED)

    # Réseaux
    h_rt_s1 = create_horaire(l1_rt, "Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_rt_s2 = create_horaire(l1_rt, "Semestre 2 - 2025-2026", STATUS_PUBLISHED)
    h_rt2_s1 = create_horaire(l2_rt, "Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_rt2_s2 = create_horaire(l2_rt, "Semestre 2 - 2025-2026", STATUS_PUBLISHED)

    # Secrétariat
    h_sd_s1 = create_horaire(l1_sd, "Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_sd_s2 = create_horaire(l1_sd, "Semestre 2 - 2025-2026", STATUS_PUBLISHED)
    h_sd2_s1 = create_horaire(l2_sd, "Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_sd2_s2 = create_horaire(l2_sd, "Semestre 2 - 2025-2026", STATUS_PUBLISHED)

    # ------------------------------------------------------------------
    # 9. Horaires globaux (examens)
    # ------------------------------------------------------------------
    def create_horaire_examen(promotion, titre, status):
        return create_horaire(promotion, titre, status, type_horaire=TYPE_EXAMEN)

    # Examens Génie Logiciel
    h_gl_s1_session = create_horaire_examen(l1_gl, "Session Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_gl_s1_rattrapage = create_horaire_examen(l1_gl, "Rattrapage Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_gl_s2_session = create_horaire_examen(l1_gl, "Session Semestre 2 - 2025-2026", STATUS_DRAFT)
    h_gl_s2_rattrapage = create_horaire_examen(l1_gl, "Rattrapage Semestre 2 - 2025-2026", STATUS_DRAFT)

    h_l2_s1_session = create_horaire_examen(l2_gl, "Session Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_l2_s1_rattrapage = create_horaire_examen(l2_gl, "Rattrapage Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_l2_s2_session = create_horaire_examen(l2_gl, "Session Semestre 2 - 2025-2026", STATUS_DRAFT)
    h_l2_s2_rattrapage = create_horaire_examen(l2_gl, "Rattrapage Semestre 2 - 2025-2026", STATUS_DRAFT)

    h_l3_s1_session = create_horaire_examen(l3_gl, "Session Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_l3_s1_rattrapage = create_horaire_examen(l3_gl, "Rattrapage Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_l3_s2_session = create_horaire_examen(l3_gl, "Session Semestre 2 - 2025-2026", STATUS_DRAFT)
    h_l3_s2_rattrapage = create_horaire_examen(l3_gl, "Rattrapage Semestre 2 - 2025-2026", STATUS_DRAFT)

    # Examens Sciences Commerciales
    h_sc_s1_session = create_horaire_examen(l1_sc, "Session Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_sc_s1_rattrapage = create_horaire_examen(l1_sc, "Rattrapage Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_sc_s2_session = create_horaire_examen(l1_sc, "Session Semestre 2 - 2025-2026", STATUS_DRAFT)
    h_sc_s2_rattrapage = create_horaire_examen(l1_sc, "Rattrapage Semestre 2 - 2025-2026", STATUS_DRAFT)

    # Examens Réseaux
    h_rt_s1_session = create_horaire_examen(l1_rt, "Session Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_rt_s1_rattrapage = create_horaire_examen(l1_rt, "Rattrapage Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_rt_s2_session = create_horaire_examen(l1_rt, "Session Semestre 2 - 2025-2026", STATUS_DRAFT)
    h_rt_s2_rattrapage = create_horaire_examen(l1_rt, "Rattrapage Semestre 2 - 2025-2026", STATUS_DRAFT)

    # Examens Secrétariat
    h_sd_s1_session = create_horaire_examen(l1_sd, "Session Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_sd_s1_rattrapage = create_horaire_examen(l1_sd, "Rattrapage Semestre 1 - 2025-2026", STATUS_PUBLISHED)
    h_sd_s2_session = create_horaire_examen(l1_sd, "Session Semestre 2 - 2025-2026", STATUS_DRAFT)
    h_sd_s2_rattrapage = create_horaire_examen(l1_sd, "Rattrapage Semestre 2 - 2025-2026", STATUS_DRAFT)

    # ------------------------------------------------------------------
    # 10. Créneaux horaires (cours) - cohérents avec les enseignants assignés
    # ------------------------------------------------------------------
    Creneau_Horaire.objects.all().delete()

    def create_creneau_cours(jours, heure, cours, horaire, status):
        """Crée un créneau de cours en utilisant l'enseignant assigné au cours."""
        return Creneau_Horaire.objects.get_or_create(
            jours=jours, heure=heure, cours=cours,
            personnel=cours.enseignant, horaire=horaire,
            defaults={'status': status, 'type_horaire': TYPE_COURS}
        )[0]

    def create_creneau_examen(date, heure, cours, horaire, status):
        """Crée un créneau d'examen en utilisant l'enseignant assigné au cours."""
        return Creneau_Horaire.objects.get_or_create(
            date=date, heure=heure, cours=cours,
            personnel=cours.enseignant, horaire=horaire,
            defaults={'status': status, 'type_horaire': TYPE_EXAMEN}
        )[0]

    # L1 GL - Semestre 1 (DRAFT)
    create_creneau_cours("Lundi", "08:00:00", c_gl1_1, h_l1_s1, STATUS_DRAFT)
    create_creneau_cours("Mercredi", "08:00:00", c_gl1_3, h_l1_s1, STATUS_DRAFT)
    create_creneau_cours("Vendredi", "11:40:00", c_gl1_2, h_l1_s1, STATUS_DRAFT)

    # L1 GL - Semestre 2 (PROPOSED)
    create_creneau_cours("Mardi", "11:40:00", c_gl1_2, h_l1_s2, STATUS_PROPOSED)
    create_creneau_cours("Jeudi", "08:00:00", c_gl1_4, h_l1_s2, STATUS_PROPOSED)

    # L2 GL - Semestre 1 (CONFIRMED)
    create_creneau_cours("Lundi", "11:40:00", c_gl2_1, h_l2_s1, STATUS_CONFIRMED)
    create_creneau_cours("Mardi", "08:00:00", c_gl2_3, h_l2_s1, STATUS_CONFIRMED)
    create_creneau_cours("Samedi", "11:40:00", c_gl2_2, h_l2_s1, STATUS_CONFIRMED)

    # L2 GL - Semestre 2 (CONFIRMED)
    create_creneau_cours("Vendredi", "08:00:00", c_gl2_4, h_l2_s2, STATUS_CONFIRMED)
    create_creneau_cours("Mercredi", "11:40:00", c_gl2_1, h_l2_s2, STATUS_CONFIRMED)

    # L3 GL - Semestre 1 (PUBLISHED)
    # prof_gl3 enseigne Sécurité Informatique
    create_creneau_cours("Lundi", "11:40:00", c_gl3_1, h_l3_s1, STATUS_PUBLISHED)
    # prof_gl1 enseigne Réseaux Avancés (Mercredi 11:40 déjà utilisé par L2 S1 ? non, L2 S1 c'est Lundi 11:40 et Mardi 08:00)
    create_creneau_cours("Mercredi", "11:40:00", c_gl3_2, h_l3_s1, STATUS_PUBLISHED)
    # prof_gl2 enseigne Cloud Computing (Vendredi 08:00 déjà utilisé par L2 S2 ? non, L2 S2 c'est Vendredi 08:00 pour c_gl2_4 enseigné par prof_gl2 !)
    # Conflit : prof_gl2 a Vendredi 08:00 dans L2 S2 (c_gl2_4) et L3 S1 (c_gl3_3)
    # Changeons c_gl3_3 à Samedi 08:00
    create_creneau_cours("Samedi", "08:00:00", c_gl3_3, h_l3_s1, STATUS_PUBLISHED)

    # L3 GL - Semestre 2 (PUBLISHED)
    # prof_gl3 enseigne Big Data (Mardi 11:40 déjà utilisé par L1 S2 ? non, L1 S2 c'est Mardi 11:40 pour c_gl1_2 enseigné par prof_gl2)
    create_creneau_cours("Mardi", "11:40:00", c_gl3_4, h_l3_s2, STATUS_PUBLISHED)
    # prof_gl3 enseigne Sécurité Informatique (Samedi 08:00 déjà utilisé par L3 S1 ? non, L3 S1 c'est Samedi 08:00 pour c_gl3_3 enseigné par prof_gl2)
    # prof_gl3 a Samedi 08:00 dans L3 S1 (c_gl3_3 est enseigné par prof_gl2, pas prof_gl3)
    # Donc prof_gl3 peut avoir Samedi 11:40
    create_creneau_cours("Jeudi", "11:40:00", c_gl3_1, h_l3_s2, STATUS_PUBLISHED)

    # Sciences Commerciales L1 - Semestre 1 (PUBLISHED)
    create_creneau_cours("Lundi", "08:00:00", c_sc1_1, h_sc_s1, STATUS_PUBLISHED)
    create_creneau_cours("Mercredi", "11:40:00", c_sc1_2, h_sc_s1, STATUS_PUBLISHED)

    # Sciences Commerciales L1 - Semestre 2 (PUBLISHED)
    create_creneau_cours("Mardi", "08:00:00", c_sc1_1, h_sc_s2, STATUS_PUBLISHED)
    create_creneau_cours("Jeudi", "11:40:00", c_sc1_2, h_sc_s2, STATUS_PUBLISHED)

    # Sciences Commerciales L2 - Semestre 1 (PUBLISHED)
    create_creneau_cours("Lundi", "11:40:00", c_sc2_1, h_sc2_s1, STATUS_PUBLISHED)
    create_creneau_cours("Vendredi", "08:00:00", c_sc2_2, h_sc2_s1, STATUS_PUBLISHED)

    # Sciences Commerciales L2 - Semestre 2 (PUBLISHED)
    create_creneau_cours("Mercredi", "08:00:00", c_sc2_1, h_sc2_s2, STATUS_PUBLISHED)

    # Réseaux L1 - Semestre 1 (PUBLISHED)
    create_creneau_cours("Mardi", "08:00:00", c_rt1_1, h_rt_s1, STATUS_PUBLISHED)
    create_creneau_cours("Jeudi", "11:40:00", c_rt1_2, h_rt_s1, STATUS_PUBLISHED)

    # Réseaux L1 - Semestre 2 (PUBLISHED)
    create_creneau_cours("Lundi", "11:40:00", c_rt1_1, h_rt_s2, STATUS_PUBLISHED)
    create_creneau_cours("Vendredi", "08:00:00", c_rt1_2, h_rt_s2, STATUS_PUBLISHED)

    # Réseaux L2 - Semestre 1 (PUBLISHED)
    create_creneau_cours("Mercredi", "08:00:00", c_rt2_1, h_rt2_s1, STATUS_PUBLISHED)
    create_creneau_cours("Samedi", "11:40:00", c_rt2_2, h_rt2_s1, STATUS_PUBLISHED)

    # Réseaux L2 - Semestre 2 (PUBLISHED)
    create_creneau_cours("Mardi", "11:40:00", c_rt2_1, h_rt2_s2, STATUS_PUBLISHED)

    # Secrétariat L1 - Semestre 1 (PUBLISHED)
    create_creneau_cours("Lundi", "11:40:00", c_sd1_1, h_sd_s1, STATUS_PUBLISHED)
    create_creneau_cours("Mercredi", "08:00:00", c_sd1_2, h_sd_s1, STATUS_PUBLISHED)

    # Secrétariat L1 - Semestre 2 (PUBLISHED)
    create_creneau_cours("Mardi", "11:40:00", c_sd1_1, h_sd_s2, STATUS_PUBLISHED)
    create_creneau_cours("Vendredi", "08:00:00", c_sd1_2, h_sd_s2, STATUS_PUBLISHED)

    # Secrétariat L2 - Semestre 1 (PUBLISHED)
    create_creneau_cours("Jeudi", "08:00:00", c_sd2_1, h_sd2_s1, STATUS_PUBLISHED)
    create_creneau_cours("Samedi", "11:40:00", c_sd2_2, h_sd2_s1, STATUS_PUBLISHED)

    # Secrétariat L2 - Semestre 2 (PUBLISHED)
    create_creneau_cours("Mercredi", "11:40:00", c_sd2_1, h_sd2_s2, STATUS_PUBLISHED)

    # ------------------------------------------------------------------
    # 11. Créneaux d'examens
    # ------------------------------------------------------------------
    # L1 GL
    create_creneau_examen(datetime.date(2026, 6, 15), "11:40:00", c_gl1_1, h_gl_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 16), "08:00:00", c_gl1_2, h_gl_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 22), "08:00:00", c_gl1_1, h_gl_s1_rattrapage, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 23), "11:40:00", c_gl1_2, h_gl_s1_rattrapage, STATUS_PUBLISHED)

    # L2 GL
    create_creneau_examen(datetime.date(2026, 6, 17), "08:00:00", c_gl2_1, h_l2_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 18), "11:40:00", c_gl2_2, h_l2_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 24), "11:40:00", c_gl2_1, h_l2_s1_rattrapage, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 25), "08:00:00", c_gl2_2, h_l2_s1_rattrapage, STATUS_PUBLISHED)

    # L3 GL
    create_creneau_examen(datetime.date(2026, 6, 19), "11:40:00", c_gl3_1, h_l3_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 20), "08:00:00", c_gl3_2, h_l3_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 26), "08:00:00", c_gl3_1, h_l3_s1_rattrapage, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 27), "11:40:00", c_gl3_2, h_l3_s1_rattrapage, STATUS_PUBLISHED)

    # Sciences Commerciales
    create_creneau_examen(datetime.date(2026, 6, 15), "08:00:00", c_sc1_1, h_sc_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 22), "08:00:00", c_sc1_1, h_sc_s1_rattrapage, STATUS_PUBLISHED)

    # Réseaux
    create_creneau_examen(datetime.date(2026, 6, 16), "11:40:00", c_rt1_1, h_rt_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 23), "11:40:00", c_rt1_1, h_rt_s1_rattrapage, STATUS_PUBLISHED)

    # Secrétariat
    create_creneau_examen(datetime.date(2026, 6, 17), "08:00:00", c_sd1_1, h_sd_s1_session, STATUS_PUBLISHED)
    create_creneau_examen(datetime.date(2026, 6, 24), "08:00:00", c_sd1_1, h_sd_s1_rattrapage, STATUS_PUBLISHED)

    # ------------------------------------------------------------------
    # 12. Propositions isolées (sans horaire)
    # ------------------------------------------------------------------
    Creneau_Horaire.objects.get_or_create(
        jours="Mardi", heure="08:00:00", cours=c_gl1_2,
        personnel=c_gl1_2.enseignant, horaire=None,
        defaults={
            'status': STATUS_PROPOSED,
            'type_horaire': TYPE_COURS,
            'annotations': "Proposition pour un créneau supplémentaire de Base de Données NoSQL"
        }
    )

    Creneau_Horaire.objects.get_or_create(
        jours="Vendredi", heure="11:40:00", cours=c_gl2_2,
        personnel=c_gl2_2.enseignant, horaire=None,
        defaults={
            'status': STATUS_PROPOSED,
            'type_horaire': TYPE_COURS,
            'annotations': "Proposition pour Intelligence Artificielle"
        }
    )

    # ------------------------------------------------------------------
    # 13. Vérification finale
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

    # Vérifier la cohérence enseignant/cours
    creneaux_incoherents = []
    for creneau in Creneau_Horaire.objects.select_related('cours', 'personnel'):
        if creneau.cours.enseignant and creneau.personnel != creneau.cours.enseignant:
            creneaux_incoherents.append(creneau)
    if creneaux_incoherents:
        print(f"\n⚠️  ATTENTION : {len(creneaux_incoherents)} créneau(x) avec enseignant incohérent :")
        for c in creneaux_incoherents:
            print(f"  - {c.cours.titre} : enseignant cours={c.cours.enseignant}, créneau={c.personnel}")
    else:
        print("✅ Vérification : tous les créneaux utilisent l'enseignant assigné au cours.")

    print("\n" + "=" * 60)
    print("Base de données prête !")
    print("=" * 60)
    print("Utilisateurs de test :")
    print("─" * 60)
    print("CHEFS DE FILIÈRE :")
    print("  chef      (MUKENDI Alain)    — Génie Logiciel")
    print("  chef2     (KABEYA Pierre)    — Sciences Commerciales")
    print("  chef3     (KASONGO Luc)      — Réseaux")
    print("  chef_sd   (NZUZI Béatrice)   — Secrétariat")
    print("ENSEIGNANTS :")
    print("  prof      (TSHIMANGA Jean)   — Génie Logiciel")
    print("  prof2     (MULUMBA Paul)     — Génie Logiciel")
    print("  prof3     (MULOPWE Sophie)   — Génie Logiciel")
    print("  prof_sc   (KASONGO Marie)    — Sciences Commerciales")
    print("  prof_rt   (ILUNGA Joseph)    — Réseaux")
    print("  prof_sd   (MUKENDI Esther)   — Secrétariat")
    print("SG-A :")
    print("  sga       (KASSONGO Bibiche)")
    print("ÉTUDIANTS :")
    print("  etud      (LUMUMBA Patrice)  — L1 GL")
    print("  etud2     (KABILA Joseph)    — L1 GL")
    print("  etud3     (MOBUTU Marie)     — L2 GL")
    print("  etud4     (TSHOMBE Albert)   — L3 GL")
    print("─" * 60)
    print(f"Mot de passe pour tous : demo")
    print("─" * 60)
    print(f"Filieres            : {Filiere.objects.count()}")
    print(f"Promotions          : {Promotion.objects.count()}")
    print(f"Cours               : {Cours.objects.count()}")
    print(f"Horaires de cours   : {Horaire.objects.filter(type_horaire=TYPE_COURS).count()}")
    print(f"Horaires d'examens  : {Horaire.objects.filter(type_horaire=TYPE_EXAMEN).count()}")
    print(f"Créneaux créés      : {Creneau_Horaire.objects.count()}")
    print(f"Disponibilités      : {Disponibilite.objects.count()}")
    print(f"Propositions isolées: {Creneau_Horaire.objects.filter(horaire__isnull=True).count()}")


if __name__ == "__main__":
    print("=" * 60)
    print("Horaires ESFORCA — Réinitialisation complète de la base de données")
    print("=" * 60)

    # 1. Supprimer la base de données
    reset_database()

    # 2. Supprimer les migrations
    reset_migrations()

    # 3. Régénérer et appliquer les migrations
    regenerate_and_apply_migrations()

    # 4. Peupler la base de données
    seed()