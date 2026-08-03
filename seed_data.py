import os
import django
import datetime

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
    print("Début du peuplement de la base de données ChronoPlan...")

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

    h_draft, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Semestre 1 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_COURS})
    h_proposed, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Semestre 2 - 2026", defaults={'status': STATUS_PROPOSED, 'type_horaire': TYPE_COURS})
    h_confirmed, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Semestre 1 - 2026", defaults={'status': STATUS_CONFIRMED, 'type_horaire': TYPE_COURS})
    h_l3_s1, _ = Horaire.objects.get_or_create(promotion=l3_gl, titre="Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_published_gl, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Année complète - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_published_sc, _ = Horaire.objects.get_or_create(promotion=l1_sc, titre="Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_published_rt, _ = Horaire.objects.get_or_create(promotion=l1_rt, titre="Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})
    h_published_sd, _ = Horaire.objects.get_or_create(promotion=l1_sd, titre="Semestre 1 - 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS})

    h_exam_gl, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Session de Juin 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_exam_sc, _ = Horaire.objects.get_or_create(promotion=l1_sc, titre="Session de Juin 2026", defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN})
    h_exam_draft, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Session de Juillet 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN})

    Creneau_Horaire.objects.all().delete()

    Creneau_Horaire.objects.get_or_create(jours="Lundi", heure="08:00:00", cours=c1, personnel=chef, horaire=h_draft, status=STATUS_DRAFT)
    Creneau_Horaire.objects.get_or_create(jours="Mardi", heure="11:40:00", cours=c2, personnel=prof, horaire=h_proposed, status=STATUS_PROPOSED)
    Creneau_Horaire.objects.get_or_create(jours="Jeudi", heure="11:40:00", cours=c3, personnel=prof, horaire=h_confirmed, status=STATUS_CONFIRMED)
    Creneau_Horaire.objects.get_or_create(jours="Vendredi", heure="08:00:00", cours=c1, personnel=chef, horaire=h_published_gl, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Lundi", heure="11:40:00", cours=c4, personnel=prof, horaire=h_published_sc, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Mardi", heure="08:00:00", cours=c5, personnel=chef, horaire=h_published_rt, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="11:40:00", cours=c6, personnel=prof, horaire=h_published_sd, status=STATUS_PUBLISHED)
    # Ajouter les nouveaux cours (3 par semestre)
    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="08:00:00", cours=c7, personnel=chef, horaire=h_draft, status=STATUS_DRAFT)
    Creneau_Horaire.objects.get_or_create(jours="Vendredi", heure="11:40:00", cours=c8, personnel=prof, horaire=h_proposed, status=STATUS_PROPOSED)
    Creneau_Horaire.objects.get_or_create(jours="Samedi", heure="08:00:00", cours=c9, personnel=prof, horaire=h_confirmed, status=STATUS_CONFIRMED)
    Creneau_Horaire.objects.get_or_create(jours="Lundi", heure="11:40:00", cours=c7, personnel=chef, horaire=h_l3_s1, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Samedi", heure="11:40:00", cours=c8, personnel=prof, horaire=h_l3_s1, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Jeudi", heure="08:00:00", cours=c9, personnel=prof, horaire=h_l3_s1, status=STATUS_PUBLISHED)

    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="11:40:00", cours=c1, personnel=chef, horaire=h_exam_gl, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Vendredi", heure="08:00:00", cours=c2, personnel=prof, horaire=h_exam_gl, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="08:00:00", cours=c4, personnel=prof, horaire=h_exam_sc, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Lundi", heure="08:00:00", cours=c3, personnel=prof, horaire=h_exam_draft, status=STATUS_DRAFT)

    Creneau_Horaire.objects.get_or_create(jours="Mardi", heure="08:00:00", cours=c2, personnel=prof, horaire=None, status=STATUS_PROPOSED, annotations="Proposition pour le créneau de Base de Données NoSQL")

    print("Base de données prête !")
    print("---------------------------------------")
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
    print("---------------------------------------")
    print(f"Horaires de cours  : {Horaire.objects.filter(type_horaire=TYPE_COURS).count()}")
    print(f"Horaires d'examens : {Horaire.objects.filter(type_horaire=TYPE_EXAMEN).count()}")
    print(f"Créneaux créés     : {Creneau_Horaire.objects.count()}")
    print(f"Propositions isolées (sans horaire) : {Creneau_Horaire.objects.filter(horaire__isnull=True).count()}")


if __name__ == "__main__":
    seed()