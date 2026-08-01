from django import forms

from .models import (
    Cours,
    Creneau_Horaire,
    Disponibilite,
    Etudiant,
    Filiere,
    Fonction,
    Horaire,
    Personnel,
    Promotion,
    Role,
    Utilisateur_Role,
    TYPE_COURS,
    TYPE_EXAMEN,
)

# ---------------------------------------------------------------------------
# Formulaire de base — centralise le style Tailwind commun à tous les champs
# ---------------------------------------------------------------------------

_BASE_WIDGET_CLASSES = (
    "w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 "
    "focus:ring-2 focus:ring-primary-500 outline-none"
)


class BaseForm(forms.ModelForm):
    """Formulaire de base appliquant un style Tailwind uniforme à tous les champs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            # Ne pas écraser les widgets qui ont déjà des classes personnalisées
            existing = field.widget.attrs.get("class", "")
            if existing:
                field.widget.attrs["class"] = f"{existing} {_BASE_WIDGET_CLASSES}"
            else:
                field.widget.attrs["class"] = _BASE_WIDGET_CLASSES


# ---------------------------------------------------------------------------
# Formulaires
# ---------------------------------------------------------------------------

class CreneauHoraireForm(BaseForm):
    """Formulaire de création/édition d'un créneau horaire."""

    class Meta:
        model = Creneau_Horaire
        fields = ("type_horaire", "jours", "date", "heure", "cours", "personnel", "horaire")
        widgets = {
            "heure": forms.Select(choices=[
                ("08:00:00", "08:00"),
                ("11:40:00", "11:40"),
            ]),
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["personnel"].queryset = Personnel.objects.filter(  # type: ignore
            roles_associes__role__libelle="Enseignant"
        ).distinct().order_by("nom", "post_nom")
        # On rend le champ horaire optionnel pour permettre les propositions isolées
        self.fields["horaire"].required = False
        # Rendre jours et date conditionnels selon le type
        self.fields["jours"].required = False
        self.fields["date"].required = False

    def clean(self):
        cleaned = super().clean()
        type_horaire = cleaned.get("type_horaire")
        jours = cleaned.get("jours")
        date = cleaned.get("date")
        heure = cleaned.get("heure")
        personnel = cleaned.get("personnel")

        # Validation selon le type
        if type_horaire == TYPE_COURS and not jours:
            raise forms.ValidationError("Un cours hebdomadaire doit avoir un jour de la semaine.")
        if type_horaire == TYPE_EXAMEN and not date:
            raise forms.ValidationError("Un examen doit avoir une date précise.")

        # Vérification des conflits
        if heure and personnel:
            if type_horaire == TYPE_EXAMEN and date:
                qs = Creneau_Horaire.objects.filter(
                    date=date, heure=heure, personnel=personnel
                )
                if self.instance and self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise forms.ValidationError(
                        "Ce créneau est déjà occupé par cet enseignant à cette date."
                    )
            elif type_horaire == TYPE_COURS and jours:
                qs = Creneau_Horaire.objects.filter(
                    jours=jours, heure=heure, personnel=personnel
                )
                if self.instance and self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise forms.ValidationError(
                        "Ce créneau est déjà occupé par cet enseignant."
                    )
        return cleaned


class PersonnelForm(BaseForm):
    """Formulaire de création/édition d'un membre du personnel."""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": _BASE_WIDGET_CLASSES}),
        required=False,
        label="Mot de passe",
        help_text="Laisser vide pour conserver l'ancien mot de passe.",
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.none(),
        label="Rôle",
    )

    class Meta:
        model = Personnel
        fields = ("nom", "post_nom", "sexe", "email", "matricule", "grade", "fonction")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.all().order_by("libelle")  # type: ignore
        if self.instance.pk:
            association = self.instance.roles_associes.select_related("role").first()
            if association:
                self.fields["role"].initial = association.role

    def save(self, commit=True):
        personnel = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            personnel.set_password(password)
        elif not personnel.pk:
            personnel.set_unusable_password()
        if commit:
            personnel.save()
            Utilisateur_Role.objects.update_or_create(
                id_util=personnel,
                role=self.cleaned_data["role"],
            )
        return personnel


class DisponibiliteForm(forms.ModelForm):
    """Formulaire de saisie d'une disponibilité enseignant."""

    class Meta:
        model = Disponibilite
        fields = ("jour", "heure_debut", "heure_fin", "note")
        widgets = {
            "heure_debut": forms.TimeInput(attrs={"type": "time"}),
            "heure_fin": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (
                f"{existing} {_BASE_WIDGET_CLASSES}".strip()
            )

    def clean(self):
        cleaned = super().clean()
        debut, fin = cleaned.get("heure_debut"), cleaned.get("heure_fin")
        if debut and fin and debut >= fin:
            raise forms.ValidationError(
                "L'heure de fin doit être postérieure à l'heure de début."
            )
        return cleaned


class FiliereForm(BaseForm):
    class Meta:
        model = Filiere
        fields = ("nom_filiere",)


class PromotionForm(BaseForm):
    class Meta:
        model = Promotion
        fields = ("designation", "annee_academique", "filiere")


class CoursForm(BaseForm):
    class Meta:
        model = Cours
        fields = ("titre", "duree")


class FonctionForm(BaseForm):
    class Meta:
        model = Fonction
        fields = ("intitule",)


class HoraireForm(BaseForm):
    """Formulaire de création d'un horaire global (Chef de Filière)."""

    class Meta:
        model = Horaire
        fields = ("titre", "promotion", "type_horaire")
        widgets = {
            "titre": forms.TextInput(attrs={
                "placeholder": "ex: Semestre 1 - 2026"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limiter aux promotions de la filière du chef si possible
        self.fields["promotion"].queryset = Promotion.objects.all().order_by(  # type: ignore
            "filiere__nom_filiere", "designation"
        )


class EtudiantForm(BaseForm):
    """Formulaire d'inscription d'un étudiant."""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": _BASE_WIDGET_CLASSES}),
        required=False,
        label="Mot de passe",
    )

    class Meta:
        model = Etudiant
        fields = (
            "nom",
            "post_nom",
            "sexe",
            "email",
            "num_matric",
            "date_naiss",
            "promotion",
        )
        widgets = {"date_naiss": forms.DateInput(attrs={"type": "date"})}

    def save(self, commit=True):
        etudiant = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            etudiant.set_password(password)
        elif not etudiant.pk:
            etudiant.set_unusable_password()
        if commit:
            etudiant.save()
            role, _ = Role.objects.get_or_create(libelle="Étudiant")
            Utilisateur_Role.objects.get_or_create(id_util=etudiant, role=role)
        return etudiant
