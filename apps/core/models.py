from functools import cached_property

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.urls import reverse

# ---------------------------------------------------------------------------
# Constantes partagées
# ---------------------------------------------------------------------------

#: Libellés des jours de la semaine utilisés par Creneau_Horaire et Disponibilite.
JOURS_CHOICES = [
    ("Lundi", "Lundi"),
    ("Mardi", "Mardi"),
    ("Mercredi", "Mercredi"),
    ("Jeudi", "Jeudi"),
    ("Vendredi", "Vendredi"),
    ("Samedi", "Samedi"),
]

#: Constantes de rôle — centralisées pour éviter les fautes de frappe.
ROLE_CHEF = "Chef de Filière"
ROLE_ENSEIGNANT = "Enseignant"
ROLE_ETUDIANT = "Étudiant"
ROLE_SGA = "SG-A"

#: Types d'horaire.
TYPE_COURS = "COURS"
TYPE_EXAMEN = "EXAMEN"

TYPE_HORAIRE_CHOICES = [
    (TYPE_COURS, "Cours"),
    (TYPE_EXAMEN, "Examen"),
]

#: Choix d'heures standardisés pour les créneaux et disponibilités.
HEURE_CHOICES = [
    ("08:00:00", "08:00"),
    ("11:40:00", "11:40"),
]

#: États du workflow de validation des horaires.
STATUS_DRAFT = "DRAFT"
STATUS_PROPOSED = "PROPOSED"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_PUBLISHED = "PUBLISHED"

STATUS_CHOICES = [
    (STATUS_DRAFT, "Brouillon"),
    (STATUS_PROPOSED, "Proposé (Chef Filière)"),
    (STATUS_CONFIRMED, "Confirmé (SGA)"),
    (STATUS_PUBLISHED, "Publié"),
]

#: Transitions autorisées du workflow (état courant → ensemble des états cibles).
WORKFLOW_TRANSITIONS = {
    STATUS_DRAFT: {STATUS_PROPOSED},
    STATUS_PROPOSED: {STATUS_DRAFT, STATUS_CONFIRMED},
    STATUS_CONFIRMED: {STATUS_PUBLISHED},
    STATUS_PUBLISHED: {STATUS_DRAFT},  # Dé-publication possible pour révision
}


# ---------------------------------------------------------------------------
# Gestionnaire personnalisé
# ---------------------------------------------------------------------------

class UtilisateurManager(BaseUserManager):
    """Gestionnaire d'utilisateurs personnalisé utilisant l'identifiant (email)."""

    def create_user(self, email, nom, post_nom, sexe, password=None):
        if not email:
            raise ValueError("L'utilisateur doit avoir un identifiant")
        user = self.model(
            email=email,
            nom=nom,
            post_nom=post_nom,
            sexe=sexe,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nom, post_nom, sexe, password=None):
        user = self.create_user(email, nom, post_nom, sexe, password)
        user.is_admin = True
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


# ---------------------------------------------------------------------------
# Modèle utilisateur
# ---------------------------------------------------------------------------

class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """Utilisateur de base du système, identifié par son adresse email."""

    SEXE_CHOICES = [("M", "Masculin"), ("F", "Féminin")]

    id_user = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    post_nom = models.CharField(max_length=100)
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)
    email = models.CharField(max_length=254, unique=True, verbose_name="Identifiant")
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    objects = UtilisateurManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom", "post_nom", "sexe"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["nom", "post_nom"]

    def __str__(self):
        return f"{self.nom} {self.post_nom}"

    # -- Cache des rôles --------------------------------------------------

    @cached_property
    def _roles_cache(self):
        """Ensemble des libellés de rôles associés (mis en cache par requête)."""
        return set(
            self.roles_associes.select_related("role")  # type: ignore[attr-defined]
            .values_list("role__libelle", flat=True)
        )

    @property
    def roles(self):
        """Retourne l'ensemble des libellés de rôles de l'utilisateur."""
        return self._roles_cache

    def a_role(self, libelle):
        """Point unique de contrôle des rôles définis par le diagramme UML."""
        return libelle in self._roles_cache

    @property
    def is_chef(self):
        return self.a_role(ROLE_CHEF)

    @property
    def is_enseignant(self):
        return self.a_role(ROLE_ENSEIGNANT)

    @property
    def is_etudiant(self):
        return self.a_role(ROLE_ETUDIANT)

    @property
    def is_sga(self):
        return self.a_role(ROLE_SGA)


class Fonction(models.Model):
    """Fonction occupée par le personnel (Chef de Filière, Enseignant, etc.)."""

    id_fonction = models.AutoField(primary_key=True)
    intitule = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Fonction"
        verbose_name_plural = "Fonctions"
        ordering = ["intitule"]

    def __str__(self):
        return self.intitule


class Personnel(Utilisateur):
    """Personnel académique (enseignants, administratifs)."""

    matricule = models.CharField(max_length=50, unique=True, null=True, blank=True)
    grade = models.CharField(max_length=100, null=True, blank=True)
    fonction = models.ForeignKey(
        Fonction, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="personnels",
        help_text="Fonction occupée par le personnel (Chef de Filière, Enseignant, etc.)",
    )
    filiere = models.ForeignKey(
        "Filiere", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="personnels",
        help_text="Filière assignée au personnel (essentiel pour les Chefs de Filière)",
    )

    class Meta(Utilisateur.Meta):  # type: ignore[misc]
        verbose_name = "Personnel"
        verbose_name_plural = "Personnels"

    def get_absolute_url(self):
        return reverse("manage_personnel")


class Role(models.Model):
    """Rôle métier (Chef de Filière, Enseignant, Étudiant, SG-A)."""

    id_role = models.AutoField(primary_key=True)
    libelle = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle


class Utilisateur_Role(models.Model):
    """Association many-to-many entre Utilisateur et Role (table de liaison explicite)."""

    id_util = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE, related_name="roles_associes"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Association rôle"
        verbose_name_plural = "Associations rôle"
        unique_together = ("id_util", "role")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.id_util} → {self.role}"


# ---------------------------------------------------------------------------
# Structure académique
# ---------------------------------------------------------------------------

class Filiere(models.Model):
    """Filière académique (ex. Génie Informatique)."""

    id_filiere = models.AutoField(primary_key=True)
    nom_filiere = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name = "Filière"
        verbose_name_plural = "Filières"
        ordering = ["nom_filiere"]

    def __str__(self):
        return self.nom_filiere


class Promotion(models.Model):
    """Promotion académique liée à une filière."""

    id_prom = models.AutoField(primary_key=True)
    designation = models.CharField(max_length=200)
    annee_academique = models.CharField(max_length=20)
    filiere = models.ForeignKey(
        Filiere, on_delete=models.CASCADE, related_name="promotions"
    )

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ["-annee_academique", "designation"]
        constraints = [
            models.UniqueConstraint(
                fields=("designation", "annee_academique", "filiere"),
                name="unique_promotion_filiere_annee",
            )
        ]

    def __str__(self):
        return f"{self.designation} ({self.annee_academique})"


class Etudiant(Utilisateur):
    """Étudiant inscrit dans une promotion."""

    num_matric = models.CharField(max_length=50, unique=True, null=True, blank=True)
    date_naiss = models.DateField(null=True, blank=True)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.SET_NULL, null=True, related_name="etudiants"
    )

    class Meta(Utilisateur.Meta):  # type: ignore[misc]
        verbose_name = "Étudiant"
        verbose_name_plural = "Étudiants"

    def get_absolute_url(self):
        return reverse("manage_students")


# ---------------------------------------------------------------------------
# Données de référence
# ---------------------------------------------------------------------------

class Cours(models.Model):
    """Cours académique (unité d'enseignement)."""

    id_cours = models.AutoField(primary_key=True)
    titre = models.CharField(max_length=200)
    duree = models.PositiveIntegerField(help_text="Durée en heures (ex: 30H)")
    duree_unite = models.CharField(
        max_length=10,
        choices=[("H", "Heures"), ("MIN", "Minutes")],
        default="H",
        help_text="Unité de la durée (heures par défaut)",
    )
    enseignant = models.ForeignKey(
        Personnel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cours_assignes",
        help_text="Enseignant habilité à dispenser ce cours",
    )
    promotion = models.ForeignKey(
        Promotion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cours",
        help_text="Promotion à laquelle ce cours est associé",
    )

    class Meta:
        verbose_name = "Cours"
        verbose_name_plural = "Cours"
        ordering = ["titre"]

    def __str__(self):
        return self.titre

    @property
    def duree_label(self):
        """Retourne la durée formatée avec son unité (ex: 30H)."""
        if self.duree_unite == "MIN":
            return f"{self.duree} min"
        return f"{self.duree}H"


class Horaire(models.Model):
    """
    Conteneur global d'emploi du temps pour une promotion donnée.
    Regroupe plusieurs créneaux horaires pour une validation globale.
    Peut être de type Cours ou Examen.
    """
    id_horaire = models.AutoField(primary_key=True)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="horaires"
    )
    titre = models.CharField(max_length=200, help_text="ex: Semestre 1 - 2026")
    type_horaire = models.CharField(
        max_length=10,
        choices=TYPE_HORAIRE_CHOICES,
        default=TYPE_COURS,
        help_text="Type d'horaire : Cours ou Examen",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Horaire"
        verbose_name_plural = "Horaires"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.titre} - {self.promotion}"

    def get_creneau_for_jour_heure(self, jour, heure):
        """Retourne le créneau pour un jour et une heure donnés, ou None."""
        return self.creneaux.filter(jours=jour, heure=heure).first()  # type: ignore[attr-defined]

    def peut_transitionner_vers(self, nouvel_etat):
        """Vérifie si la transition vers *nouvel_etat* est autorisée."""
        return nouvel_etat in WORKFLOW_TRANSITIONS.get(self.status, set())

    def transitionner(self, nouvel_etat):
        """Effectue la transition de statut en validant le workflow."""
        if not self.peut_transitionner_vers(nouvel_etat):
            raise ValueError(f"Transition interdite : {self.status} vers {nouvel_etat}")
        self.status = nouvel_etat
        self.save(update_fields=["status"])

    @property
    def status_label(self):
        """Retourne le libellé lisible du statut actuel."""
        return dict(STATUS_CHOICES).get(self.status, self.status)


# ---------------------------------------------------------------------------
# Planification
# ---------------------------------------------------------------------------

class Creneau_Horaire(models.Model):
    """
    Créneau horaire liant un cours, un personnel et une fonction.
    Peut être une proposition isolée d'un enseignant ou faire partie d'un Horaire.
    
    - Pour les **cours** : on utilise ``jours`` (Lundi, Mardi…) et ``heure``.
    - Pour les **examens** : on utilise ``date`` (date précise) et ``heure``.
    """

    id_chrono = models.AutoField(primary_key=True)
    type_horaire = models.CharField(
        max_length=10,
        choices=TYPE_HORAIRE_CHOICES,
        default=TYPE_COURS,
        help_text="Type de créneau : Cours (jour hebdomadaire) ou Examen (date précise)",
    )
    date = models.DateField(
        null=True, blank=True,
        help_text="Date précise pour un examen (ex: 15/06/2026). Laisser vide pour un cours hebdomadaire.",
    )
    heure = models.CharField(
        max_length=10,
        choices=HEURE_CHOICES,
        default="08:00:00",
        help_text="Heure du créneau (08:00 ou 11h40)",
    )
    jours = models.CharField(
        max_length=20, 
        choices=JOURS_CHOICES,
        null=True, blank=True,
        help_text="Jour de la semaine pour un cours hebdomadaire. Laisser vide pour un examen avec date.",
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default=STATUS_DRAFT
    )
    cours = models.ForeignKey(
        Cours, on_delete=models.CASCADE, related_name="horaires"
    )
    personnel = models.ForeignKey(
        Personnel, on_delete=models.CASCADE, related_name="dispense_cours"
    )
    horaire = models.ForeignKey(
        Horaire, on_delete=models.SET_NULL, null=True, blank=True, related_name="creneaux"
    )
    annotations = models.TextField(
        blank=True, 
        null=True, 
        help_text="Annotations ou demandes de modification de l'enseignant"
    )

    class Meta:
        verbose_name = "Créneau Horaire"
        verbose_name_plural = "Créneaux Horaires"
        ordering = ["date", "jours", "heure"]
        constraints = [
            models.UniqueConstraint(
                fields=("date", "heure", "personnel"),
                name="unique_creneau_date_personnel",
            ),
            models.UniqueConstraint(
                fields=("jours", "heure", "personnel"),
                name="unique_creneau_jour_personnel",
                condition=models.Q(date__isnull=True),
            ),
        ]

    def __str__(self):
        if self.date:
            return f"{self.cours} | {self.date.strftime('%d/%m/%Y')} {self.heure}"
        return f"{self.cours} | {self.jours} {self.heure}"

    # -- Workflow ---------------------------------------------------------

    def peut_transitionner_vers(self, nouvel_etat):
        """Vérifie si la transition vers *nouvel_etat* est autorisée."""
        return nouvel_etat in WORKFLOW_TRANSITIONS.get(self.status, set())

    def transitionner(self, nouvel_etat):
        """Effectue la transition de statut en validant le workflow."""
        if not self.peut_transitionner_vers(nouvel_etat):
            raise ValueError(f"Transition interdite : {self.status} vers {nouvel_etat}")
        self.status = nouvel_etat
        self.save(update_fields=["status"])

    @property
    def status_label(self):
        """Retourne le libellé lisible du statut actuel."""
        return dict(STATUS_CHOICES).get(self.status, self.status)


class Disponibilite(models.Model):
    """Créneau de disponibilité déclaré par un enseignant."""

    enseignant = models.ForeignKey(
        Personnel, on_delete=models.CASCADE, related_name="disponibilites"
    )
    jour = models.CharField(max_length=20, choices=JOURS_CHOICES)
    heure = models.TimeField()
    note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Disponibilité"
        verbose_name_plural = "Disponibilités"
        ordering = ["enseignant", "jour", "heure"]

    def __str__(self):
        return f"{self.enseignant} — {self.jour} {self.heure.strftime('%H:%M')}"
