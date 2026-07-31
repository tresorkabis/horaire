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

    l1_gl, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=gl)
    l2_gl, _ = Promotion.objects.get_or_create(designation="L2", annee_academique="2025-2026", filiere=gl)
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

    chef = create_actor("chef", "MUKENDI", "Alain", "Chef de Filière", Personnel, matricule="P001", grade="Professeur")
    prof = create_actor("prof", "TSHIMANGA", "Jean", "Enseignant", Personnel, matricule="P002", grade="Chef de Travaux")
    sga = create_actor("sga", "KASSONGO", "Bibiche", "SG-A", Personnel, matricule="P003", grade="Secrétaire Général")
    sga.is_staff = True
    sga.is_superuser = True
    sga.save()
    etud = create_actor("etud", "LUMUMBA", "Patrice", "Étudiant", Etudiant, num_matric="S001", date_naiss=datetime.date(2003, 1, 1), promotion=l1_gl)

    c1, _ = Cours.objects.get_or_create(titre="Algorithmique Avancée", defaults={'duree': 120})
    c2, _ = Cours.objects.get_or_create(titre="Base de Données NoSQL", defaults={'duree': 90})
    c3, _ = Cours.objects.get_or_create(titre="Architecture des Ordinateurs", defaults={'duree': 120})
    c4, _ = Cours.objects.get_or_create(titre="Marketing Digital", defaults={'duree': 90})
    c5, _ = Cours.objects.get_or_create(titre="Administration Réseau", defaults={'duree': 120})
    c6, _ = Cours.objects.get_or_create(titre="Communication Professionnelle", defaults={'duree': 90})

    f_th, _ = Fonction.objects.get_or_create(intitule="Cours Théorique")
    f_tp, _ = Fonction.objects.get_or_create(intitule="Travaux Pratiques")
    f_exam, _ = Fonction.objects.get_or_create(intitule="Examen")

    h_draft, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Semestre 1 - 2026", defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_COURS})
    h_proposed, _ = Horaire.objects.get_or_create(promotion=l1_gl, titre="Semestre 2 - 2026", defaults={'status': STATUS_PROPOSED, 'type_horaire': TYPE_COURS})
    h_confirmed, _ = Horaire.objects.get_or_create(promotion=l2_gl, titre="Semestre 1 - 2026", defaults={'status': STATUS_CONFIRMED, 'type_horaire': TYPE_COURS})
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

    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="11:40:00", cours=c1, personnel=chef, horaire=h_exam_gl, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Jeudi", heure="08:00:00", cours=c2, personnel=prof, horaire=h_exam_gl, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Vendredi", heure="11:40:00", cours=c4, personnel=prof, horaire=h_exam_sc, status=STATUS_PUBLISHED)
    Creneau_Horaire.objects.get_or_create(jours="Samedi", heure="08:00:00", cours=c3, personnel=prof, horaire=h_exam_draft, status=STATUS_DRAFT)

    Creneau_Horaire.objects.get_or_create(jours="Lundi", heure="08:00:00", cours=c2, personnel=prof, horaire=None, status=STATUS_PROPOSED, annotations="Proposition pour le créneau de Base de Données NoSQL")
    Creneau_Horaire.objects.get_or_create(jours="Mercredi", heure="08:00:00", cours=c3, personnel=prof, horaire=None, status=STATUS_PROPOSED, annotations="Je peux assurer ce cours le mercredi matin")

    print("Base de données prête !")
    print("---------------------------------------")
    print("Utilisateurs de test :")
    print("1. Chef Filière : chef / demo")
    print("2. Enseignant   : prof / demo")
    print("3. SGA          : sga / demo")
    print("4. Étudiant     : etud / demo")
    print("---------------------------------------")
    print(f"Horaires de cours  : {Horaire.objects.filter(type_horaire=TYPE_COURS).count()}")
    print(f"Horaires d'examens : {Horaire.objects.filter(type_horaire=TYPE_EXAMEN).count()}")
    print(f"Créneaux créés     : {Creneau_Horaire.objects.count()}")
    print(f"Propositions isolées (sans horaire) : {Creneau_Horaire.objects.filter(horaire__isnull=True).count()}")


if __name__ == "__main__":
    seed()