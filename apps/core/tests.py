from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from .models import (Creneau_Horaire, Cours, Etudiant, Filiere, Fonction,
                     Personnel, Promotion, Role, Utilisateur_Role)


class WorkflowTests(TestCase):
    def setUp(self):
        self.chef = Personnel.objects.create_user("chef@test.cd", "Chef", "Filière", "M", "secret123")
        self.chef.matricule, self.chef.grade = "P001", "Professeur"
        self.chef.save()
        self.sga = Personnel.objects.create_user("sga@test.cd", "SGA", "Académique", "F", "secret123")
        self.sga.matricule, self.sga.grade = "P002", "Secrétaire"
        self.sga.save()
        self.teacher = Personnel.objects.create_user("ens@test.cd", "Enseignant", "Test", "M", "secret123")
        self.teacher.matricule, self.teacher.grade = "P003", "Assistant"
        self.teacher.save()
        self.other_teacher = Personnel.objects.create_user("other@test.cd", "Autre", "Prof", "F", "secret123")
        self.other_teacher.matricule, self.other_teacher.grade = "P004", "Assistant"
        self.other_teacher.save()
        for user, label in ((self.chef, "Chef de Filière"), (self.sga, "SG-A"), (self.teacher, "Enseignant"), (self.other_teacher, "Enseignant")):
            role, _ = Role.objects.get_or_create(libelle=label)
            Utilisateur_Role.objects.create(id_util=user, role=role)
        cours = Cours.objects.create(titre="Django", duree=120)
        fonction = Fonction.objects.create(intitule="Cours théorique")
        self.horaire = Creneau_Horaire.objects.create(heure=time(8), jours="Lundi", cours=cours, personnel=self.teacher, fonction=fonction, status="PROPOSED")

    def test_sga_confirme_puis_chef_publie(self):
        self.client.force_login(self.sga)
        self.client.post(reverse("confirm_schedule", args=[self.horaire.pk]))
        self.horaire.refresh_from_db()
        self.assertEqual(self.horaire.status, "CONFIRMED")
        self.client.force_login(self.chef)
        self.client.post(reverse("publish_schedule", args=[self.horaire.pk]))
        self.horaire.refresh_from_db()
        self.assertEqual(self.horaire.status, "PUBLISHED")

    def test_transition_get_interdite(self):
        self.client.force_login(self.sga)
        self.assertEqual(self.client.get(reverse("confirm_schedule", args=[self.horaire.pk])).status_code, 405)

    def test_enseignant_ne_peut_annoter_que_son_horaire(self):
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.post(reverse("annotate_schedule", args=[self.horaire.pk]), {"annotations": "Non"}).status_code, 404)

    def test_disponibilite_est_enregistree(self):
        self.client.force_login(self.teacher)
        response = self.client.post(reverse("submit_availability"), {"jour[]": ["Mardi"], "debut[]": ["09:00"], "fin[]": ["11:00"], "note[]": [""]})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.teacher.disponibilites.count(), 1)

    def test_transition_metier_invalide_est_bloquee(self):
        self.horaire.status = "DRAFT"
        self.horaire.save(update_fields=["status"])
        with self.assertRaises(ValueError):
            self.horaire.transitionner("PUBLISHED")

    def test_sga_gere_les_filieres(self):
        self.client.force_login(self.sga)
        response = self.client.post(
            reverse("manage_referentiel", args=["filieres"]),
            {"nom_filiere": "Sciences informatiques"},
        )
        self.assertRedirects(response, reverse("manage_referentiel", args=["filieres"]))
        self.assertTrue(Filiere.objects.filter(nom_filiere="Sciences informatiques").exists())

    def test_enseignant_ne_gere_pas_les_referentiels(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("manage_referentiel", args=["cours"]))
        self.assertRedirects(response, reverse("dashboard"))

    def test_toutes_les_pages_enseignant_repondent(self):
        self.client.force_login(self.teacher)
        for url in (reverse("dashboard"), reverse("schedule_list"), reverse("submit_availability")):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_toutes_les_pages_sga_repondent(self):
        self.client.force_login(self.sga)
        urls = [reverse("dashboard"), reverse("schedule_list"), reverse("manage_personnel"),
                reverse("manage_students")]
        urls += [reverse("manage_referentiel", args=[name]) for name in ("filieres", "promotions", "cours", "fonctions")]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_role_sga_prioritaire_sur_enseignant(self):
        role_enseignant, _ = Role.objects.get_or_create(libelle="Enseignant")
        Utilisateur_Role.objects.get_or_create(id_util=self.sga, role=role_enseignant)
        self.client.force_login(self.sga)
        response = self.client.get(reverse("dashboard"))
        self.assertTrue(response.context["is_sga"])

    def test_creation_horaire_par_chef(self):
        self.client.force_login(self.chef)
        response = self.client.post(reverse("create_schedule"), {
            "jours": "Mercredi", "heure": "13:00", "cours": self.horaire.cours_id,
            "personnel": self.teacher.pk, "fonction": self.horaire.fonction_id,
            "status": "DRAFT",
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(Creneau_Horaire.objects.filter(jours="Mercredi", heure="13:00").exists())


class StudentVisibilityTests(TestCase):
    def test_visiteur_est_redirige_vers_la_connexion_existante(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f'{reverse("login")}?next={reverse("dashboard")}')

    def test_heritage_et_relations_uml(self):
        filiere = Filiere.objects.create(nom_filiere="Informatique")
        promotion = Promotion.objects.create(designation="L3", annee_academique="2025-2026", filiere=filiere)
        student = Etudiant.objects.create_user("etu@test.cd", "Etudiant", "Test", "M", "secret123")
        student.num_matric, student.date_naiss, student.promotion = "E001", date(2000, 1, 1), promotion
        student.save()
        self.assertEqual(student.promotion.filiere, filiere)
        self.assertIn(student, promotion.etudiants.all())
