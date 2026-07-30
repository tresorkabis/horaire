import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.models import (
    Utilisateur, Personnel, Etudiant, Role, Filiere, 
    Promotion, Cours, Fonction, Creneau_Horaire, Utilisateur_Role
)

def seed():
    print("Début du peuplement de la base de données ChronoPlan...")

    # 1. Rôles
    roles_names = ['Chef de Filière', 'Enseignant', 'Étudiant', 'SG-A']
    roles = {name: Role.objects.get_or_create(libelle=name)[0] for name in roles_names}

    # 2. Structure Académique
    # 4 filières comme demandé
    gl, _ = Filiere.objects.get_or_create(nom_filiere="Génie Logiciel")
    sc, _ = Filiere.objects.get_or_create(nom_filiere="Sciences Commerciales")
    rt, _ = Filiere.objects.get_or_create(nom_filiere="Réseaux et Techniques de Maintenance")
    sd, _ = Filiere.objects.get_or_create(nom_filiere="Secrétariat de Direction")

    # Promotions pour chaque filière
    l1_gl, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=gl)
    l2_gl, _ = Promotion.objects.get_or_create(designation="L2", annee_academique="2025-2026", filiere=gl)
    l1_sc, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=sc)
    l1_rt, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=rt)
    l1_sd, _ = Promotion.objects.get_or_create(designation="L1", annee_academique="2025-2026", filiere=sd)

    # 3. Création des Acteurs (Passwords: password123)
    def create_actor(email, nom, pnom, role_name, model_class, **extra):
        user = model_class.objects.filter(email=email).first()
        if not user:
            user = model_class.objects.create_user(email=email, nom=nom, post_nom=pnom, sexe='M', password='password123')
        for field, value in extra.items():
            setattr(user, field, value)
        user.save()
        Utilisateur_Role.objects.get_or_create(id_util=user, role=roles[role_name])
        return user

    chef = create_actor("chef@demo.com", "MUKENDI", "Alain", "Chef de Filière", Personnel, matricule="P001", grade="Professeur")
    prof = create_actor("enseignant@demo.com", "TSHIMANGA", "Jean", "Enseignant", Personnel, matricule="P002", grade="Chef de Travaux")
    sga = create_actor("sga@demo.com", "KASSONGO", "Bibiche", "SG-A", Personnel, matricule="P003", grade="Secrétaire Général")
    
    # SGA has admin access
    sga.is_staff = True
    sga.is_superuser = True
    sga.save()

    etud = create_actor("etudiant@demo.com", "LUMUMBA", "Patrice", "Étudiant", Etudiant, num_matric="S001", date_naiss=datetime.date(2003,1,1), promotion=l1_gl)

    # 4. Cours & Fonctions
    c1, _ = Cours.objects.get_or_create(titre="Algorithmique Avancée", defaults={'duree': 120})
    c2, _ = Cours.objects.get_or_create(titre="Base de Données NoSQL", defaults={'duree': 90})
    c3, _ = Cours.objects.get_or_create(titre="Architecture des Ordinateurs", defaults={'duree': 120})

    f_th, _ = Fonction.objects.get_or_create(intitule="Cours Théorique")
    f_tp, _ = Fonction.objects.get_or_create(intitule="Travaux Pratiques")

    # 5. Horaires (Différents états)
    # Brouillon (Chef) - Génie Logiciel L1
    horaire1 = Creneau_Horaire.objects.get_or_create(heure=datetime.time(8,0), jours="Lundi", cours=c1, personnel=chef, defaults={'fonction': f_th, 'status': 'DRAFT'})[0]
    horaire1.promotions.set([l1_gl])

    # Proposé (En attente SGA) - Génie Logiciel L1
    horaire2 = Creneau_Horaire.objects.get_or_create(heure=datetime.time(10,0), jours="Mardi", cours=c2, personnel=prof, defaults={'fonction': f_tp, 'status': 'PROPOSED'})[0]
    horaire2.promotions.set([l1_gl])

    # Confirmé (Par SGA, en attente publication Chef) - Génie Logiciel L2
    horaire3 = Creneau_Horaire.objects.get_or_create(heure=datetime.time(14,0), jours="Jeudi", cours=c3, personnel=prof, defaults={'fonction': f_th, 'status': 'CONFIRMED'})[0]
    horaire3.promotions.set([l2_gl])

    # Publié (Visible par tous) - Génie Logiciel L1
    horaire4 = Creneau_Horaire.objects.get_or_create(heure=datetime.time(8,0), jours="Vendredi", cours=c1, personnel=chef, defaults={'fonction': f_tp, 'status': 'PUBLISHED'})[0]
    horaire4.promotions.set([l1_gl])

    # Ajout d'horaires pour d'autres filières
    # Sciences Commerciales L1 - Publié
    c4, _ = Cours.objects.get_or_create(titre="Marketing Digital", defaults={'duree': 90})
    horaire5 = Creneau_Horaire.objects.get_or_create(heure=datetime.time(10,0), jours="Lundi", cours=c4, personnel=prof, defaults={'fonction': f_th, 'status': 'PUBLISHED'})[0]
    horaire5.promotions.set([l1_sc])

    # Réseaux et Techniques de Maintenance L1 - Publié
    c5, _ = Cours.objects.get_or_create(titre="Administration Réseau", defaults={'duree': 120})
    horaire6 = Creneau_Horaire.objects.get_or_create(heure=datetime.time(14,0), jours="Mardi", cours=c5, personnel=chef, defaults={'fonction': f_tp, 'status': 'PUBLISHED'})[0]
    horaire6.promotions.set([l1_rt])

    # Secrétariat de Direction L1 - Publié
    c6, _ = Cours.objects.get_or_create(titre="Communication Professionnelle", defaults={'duree': 90})
    horaire7 = Creneau_Horaire.objects.get_or_create(heure=datetime.time(9,0), jours="Mercredi", cours=c6, personnel=prof, defaults={'fonction': f_th, 'status': 'PUBLISHED'})[0]
    horaire7.promotions.set([l1_sd])

    print("Base de données prête !")
    print("---------------------------------------")
    print("Utilisateurs de test :")
    print("1. Chef Filière : chef@demo.com / password123")
    print("2. Enseignant   : enseignant@demo.com / password123")
    print("3. SGA          : sga@demo.com / password123")
    print("4. Étudiant     : etudiant@demo.com / password123")

if __name__ == "__main__":
    seed()
