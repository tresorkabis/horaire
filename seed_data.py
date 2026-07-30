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

    # ------------------------------------------------------------------
    # 1. Rôles
    # ------------------------------------------------------------------
    roles_names = ['Chef de Filière', 'Enseignant', 'Étudiant', 'SG-A']
    roles = {name: Role.objects.get_or_create(libelle=name)[0] for name in roles_names}

    # ------------------------------------------------------------------
    # 2. Structure Académique
    # ------------------------------------------------------------------
    gl, _ = Filiere.objects.get_or_create(nom_filiere="Génie Logiciel")
    sc, _ = Filiere.objects.get_or_create(nom_filiere="Sciences Commerciales")
    rt, _ = Filiere.objects.get_or_create(nom_filiere="Réseaux et Techniques de Maintenance")
    sd, _ = Filiere.objects.get_or_create(nom_filiere="Secrétariat de Direction")

    # Promotions
    l1_gl, _ = Promotion.objects.get_or_create(
        designation="L1", annee_academique="2025-2026", filiere=gl
    )
    l2_gl, _ = Promotion.objects.get_or_create(
        designation="L2", annee_academique="2025-2026", filiere=gl
    )
    l1_sc, _ = Promotion.objects.get_or_create(
        designation="L1", annee_academique="2025-2026", filiere=sc
    )
    l1_rt, _ = Promotion.objects.get_or_create(
        designation="L1", annee_academique="2025-2026", filiere=rt
    )
    l1_sd, _ = Promotion.objects.get_or_create(
        designation="L1", annee_academique="2025-2026", filiere=sd
    )

    # ------------------------------------------------------------------
    # 3. Création des Acteurs
    # ------------------------------------------------------------------
    def create_actor(email, nom, pnom, role_name, model_class, **extra):
        user = model_class.objects.filter(email=email).first()
        if not user:
            user = model_class.objects.create_user(
                email=email, nom=nom, post_nom=pnom, sexe='M',
                password='password123'
            )
        for field, value in extra.items():
            setattr(user, field, value)
        user.save()
        Utilisateur_Role.objects.get_or_create(id_util=user, role=roles[role_name])
        return user

    chef = create_actor(
        "chef@demo.com", "MUKENDI", "Alain", "Chef de Filière",
        Personnel, matricule="P001", grade="Professeur"
    )
    prof = create_actor(
        "enseignant@demo.com", "TSHIMANGA", "Jean", "Enseignant",
        Personnel, matricule="P002", grade="Chef de Travaux"
    )
    sga = create_actor(
        "sga@demo.com", "KASSONGO", "Bibiche", "SG-A",
        Personnel, matricule="P003", grade="Secrétaire Général"
    )
    # Le SGA a accès à l'admin
    sga.is_staff = True
    sga.is_superuser = True
    sga.save()

    etud = create_actor(
        "etudiant@demo.com", "LUMUMBA", "Patrice", "Étudiant",
        Etudiant, num_matric="S001", date_naiss=datetime.date(2003, 1, 1),
        promotion=l1_gl
    )

    # ------------------------------------------------------------------
    # 4. Cours & Fonctions
    # ------------------------------------------------------------------
    c1, _ = Cours.objects.get_or_create(titre="Algorithmique Avancée", defaults={'duree': 120})
    c2, _ = Cours.objects.get_or_create(titre="Base de Données NoSQL", defaults={'duree': 90})
    c3, _ = Cours.objects.get_or_create(titre="Architecture des Ordinateurs", defaults={'duree': 120})
    c4, _ = Cours.objects.get_or_create(titre="Marketing Digital", defaults={'duree': 90})
    c5, _ = Cours.objects.get_or_create(titre="Administration Réseau", defaults={'duree': 120})
    c6, _ = Cours.objects.get_or_create(titre="Communication Professionnelle", defaults={'duree': 90})

    f_th, _ = Fonction.objects.get_or_create(intitule="Cours Théorique")
    f_tp, _ = Fonction.objects.get_or_create(intitule="Travaux Pratiques")
    f_exam, _ = Fonction.objects.get_or_create(intitule="Examen")

    # ------------------------------------------------------------------
    # 5. HORAIRES DE COURS
    # ------------------------------------------------------------------

    # 5a. Horaire COURS - BROUILLON pour Génie Logiciel L1
    h_draft, _ = Horaire.objects.get_or_create(
        promotion=l1_gl,
        titre="Semestre 1 - 2026",
        defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_COURS}
    )

    # 5b. Horaire COURS - PROPOSÉ pour Génie Logiciel L1 (en attente SGA)
    h_proposed, _ = Horaire.objects.get_or_create(
        promotion=l1_gl,
        titre="Semestre 2 - 2026",
        defaults={'status': STATUS_PROPOSED, 'type_horaire': TYPE_COURS}
    )

    # 5c. Horaire COURS - CONFIRMÉ pour Génie Logiciel L2 (en attente publication Chef)
    h_confirmed, _ = Horaire.objects.get_or_create(
        promotion=l2_gl,
        titre="Semestre 1 - 2026",
        defaults={'status': STATUS_CONFIRMED, 'type_horaire': TYPE_COURS}
    )

    # 5d. Horaire COURS - PUBLIÉ pour Génie Logiciel L1 (visible par les étudiants)
    h_published_gl, _ = Horaire.objects.get_or_create(
        promotion=l1_gl,
        titre="Année complète - 2026",
        defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS}
    )

    # 5e. Horaires COURS - PUBLIÉS pour les autres filières
    h_published_sc, _ = Horaire.objects.get_or_create(
        promotion=l1_sc,
        titre="Semestre 1 - 2026",
        defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS}
    )
    h_published_rt, _ = Horaire.objects.get_or_create(
        promotion=l1_rt,
        titre="Semestre 1 - 2026",
        defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS}
    )
    h_published_sd, _ = Horaire.objects.get_or_create(
        promotion=l1_sd,
        titre="Semestre 1 - 2026",
        defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_COURS}
    )

    # ------------------------------------------------------------------
    # 6. HORAIRES D'EXAMENS
    # ------------------------------------------------------------------

    # 6a. Horaire EXAMEN - PUBLIÉ pour Génie Logiciel L1
    h_exam_gl, _ = Horaire.objects.get_or_create(
        promotion=l1_gl,
        titre="Session de Juin 2026",
        defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN}
    )

    # 6b. Horaire EXAMEN - PUBLIÉ pour Sciences Commerciales L1
    h_exam_sc, _ = Horaire.objects.get_or_create(
        promotion=l1_sc,
        titre="Session de Juin 2026",
        defaults={'status': STATUS_PUBLISHED, 'type_horaire': TYPE_EXAMEN}
    )

    # 6c. Horaire EXAMEN - BROUILLON pour Génie Logiciel L2 (en préparation)
    h_exam_draft, _ = Horaire.objects.get_or_create(
        promotion=l2_gl,
        titre="Session de Juillet 2026",
        defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN}
    )

    # ------------------------------------------------------------------
    # 7. Créneaux horaires liés aux horaires de COURS
    # ------------------------------------------------------------------

    # Créneaux pour l'horaire COURS BROUILLON (Génie Logiciel L1)
    Creneau_Horaire.objects.get_or_create(
        jours="Lundi", heure=datetime.time(8, 0),
        cours=c1, personnel=chef, fonction=f_th,
        horaire=h_draft, status=STATUS_DRAFT
    )

    # Créneaux pour l'horaire COURS PROPOSÉ (Génie Logiciel L1)
    Creneau_Horaire.objects.get_or_create(
        jours="Mardi", heure=datetime.time(10, 0),
        cours=c2, personnel=prof, fonction=f_tp,
        horaire=h_proposed, status=STATUS_PROPOSED
    )

    # Créneaux pour l'horaire COURS CONFIRMÉ (Génie Logiciel L2)
    Creneau_Horaire.objects.get_or_create(
        jours="Jeudi", heure=datetime.time(14, 0),
        cours=c3, personnel=prof, fonction=f_th,
        horaire=h_confirmed, status=STATUS_CONFIRMED
    )

    # Créneaux pour l'horaire COURS PUBLIÉ (Génie Logiciel L1)
    Creneau_Horaire.objects.get_or_create(
        jours="Vendredi", heure=datetime.time(8, 0),
        cours=c1, personnel=chef, fonction=f_tp,
        horaire=h_published_gl, status=STATUS_PUBLISHED
    )

    # Créneaux pour l'horaire COURS PUBLIÉ (Sciences Commerciales L1)
    Creneau_Horaire.objects.get_or_create(
        jours="Lundi", heure=datetime.time(10, 0),
        cours=c4, personnel=prof, fonction=f_th,
        horaire=h_published_sc, status=STATUS_PUBLISHED
    )

    # Créneaux pour l'horaire COURS PUBLIÉ (Réseaux L1)
    Creneau_Horaire.objects.get_or_create(
        jours="Mardi", heure=datetime.time(14, 0),
        cours=c5, personnel=chef, fonction=f_tp,
        horaire=h_published_rt, status=STATUS_PUBLISHED
    )

    # Créneaux pour l'horaire COURS PUBLIÉ (Secrétariat L1)
    Creneau_Horaire.objects.get_or_create(
        jours="Mercredi", heure=datetime.time(9, 0),
        cours=c6, personnel=prof, fonction=f_th,
        horaire=h_published_sd, status=STATUS_PUBLISHED
    )

    # ------------------------------------------------------------------
    # 8. Créneaux horaires liés aux horaires d'EXAMENS
    # ------------------------------------------------------------------

    # Créneaux pour l'horaire EXAMEN PUBLIÉ (Génie Logiciel L1)
    # Note: Lundi 8:00 est déjà pris par le cours brouillon → on utilise Mercredi 14:00
    Creneau_Horaire.objects.get_or_create(
        jours="Mercredi", heure=datetime.time(14, 0),
        cours=c1, personnel=chef, fonction=f_exam,
        horaire=h_exam_gl, status=STATUS_PUBLISHED
    )
    Creneau_Horaire.objects.get_or_create(
        jours="Jeudi", heure=datetime.time(8, 0),
        cours=c2, personnel=prof, fonction=f_exam,
        horaire=h_exam_gl, status=STATUS_PUBLISHED
    )

    # Créneaux pour l'horaire EXAMEN PUBLIÉ (Sciences Commerciales L1)
    Creneau_Horaire.objects.get_or_create(
        jours="Vendredi", heure=datetime.time(9, 0),
        cours=c4, personnel=prof, fonction=f_exam,
        horaire=h_exam_sc, status=STATUS_PUBLISHED
    )

    # Créneaux pour l'horaire EXAMEN BROUILLON (Génie Logiciel L2)
    Creneau_Horaire.objects.get_or_create(
        jours="Samedi", heure=datetime.time(8, 0),
        cours=c3, personnel=prof, fonction=f_exam,
        horaire=h_exam_draft, status=STATUS_DRAFT
    )

    # ------------------------------------------------------------------
    # 9. Propositions isolées d'enseignants (sans horaire global)
    #    → visibles dans la liste des propositions du Chef de Filière
    # ------------------------------------------------------------------
    Creneau_Horaire.objects.get_or_create(
        jours="Lundi", heure=datetime.time(14, 0),
        cours=c2, personnel=prof, fonction=f_tp,
        horaire=None, status=STATUS_PROPOSED,
        annotations="Proposition pour le créneau de Base de Données NoSQL"
    )
    Creneau_Horaire.objects.get_or_create(
        jours="Mercredi", heure=datetime.time(8, 0),
        cours=c3, personnel=prof, fonction=f_th,
        horaire=None, status=STATUS_PROPOSED,
        annotations="Je peux assurer ce cours le mercredi matin"
    )

    # ------------------------------------------------------------------
    # Résumé
    # ------------------------------------------------------------------
    print("Base de données prête !")
    print("---------------------------------------")
    print("Utilisateurs de test :")
    print("1. Chef Filière : chef@demo.com / password123")
    print("2. Enseignant   : enseignant@demo.com / password123")
    print("3. SGA          : sga@demo.com / password123")
    print("4. Étudiant     : etudiant@demo.com / password123")
    print("---------------------------------------")
    print(f"Horaires de cours  : {Horaire.objects.filter(type_horaire=TYPE_COURS).count()}")
    print(f"Horaires d'examens : {Horaire.objects.filter(type_horaire=TYPE_EXAMEN).count()}")
    print(f"Créneaux créés     : {Creneau_Horaire.objects.count()}")
    print(f"Propositions isolées (sans horaire) : {Creneau_Horaire.objects.filter(horaire__isnull=True).count()}")


if __name__ == "__main__":
    seed()