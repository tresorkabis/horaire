import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    CoursForm,
    CreneauHoraireForm,
    DisponibiliteForm,
    EtudiantForm,
    FiliereForm,
    FonctionForm,
    HoraireForm,
    PersonnelForm,
    PromotionForm,
)
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
    ROLE_CHEF,
    ROLE_ENSEIGNANT,
    ROLE_ETUDIANT,
    ROLE_SGA,
    STATUS_DRAFT,
    STATUS_PROPOSED,
    STATUS_CONFIRMED,
    STATUS_PUBLISHED,
    STATUS_CHOICES,
    TYPE_COURS,
    TYPE_EXAMEN,
)

# Nombre d'éléments par page pour la pagination
PAGINATE_BY = 25


def _roles(user):
    """Retourne l'ensemble des rôles de l'utilisateur (cache par requête via le modèle)."""
    return user.roles

def get_annee_academique():
    """
    Retourne l'année académique en cours au format "YYYY-YYYY".
    L'année académique commence en septembre et se termine en août.
    Exemple : Pour une date en septembre 2025 - août 2026, retourne "2025-2026"
    """
    today = datetime.date.today()
    # Si nous sommes entre janvier et août, l'année académique est (année-1)-année
    if today.month <= 8:
        return f"{today.year - 1}-{today.year}"
    # Si nous sommes entre septembre et décembre, l'année académique est année-(année+1)
    else:
        return f"{today.year}-{today.year + 1}"


def role_required(*allowed_roles):
    """Décorateur exigeant que l'utilisateur possède au moins un des rôles donnés."""

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not (_roles(request.user) & set(allowed_roles)):
                messages.error(request, "Accès refusé.")
                return redirect("dashboard")
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        user = authenticate(
            request,
            email=request.POST.get("email"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect("dashboard")
        messages.error(request, "Email ou mot de passe incorrect.")
    return render(request, "registration/login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


# ---------------------------------------------------------------------------
# Tableau de bord
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    """Tableau de bord personnalisé selon le rôle de l'utilisateur."""
    user = request.user
    roles = _roles(user)
    context = {"user_roles": roles, "horaires": Creneau_Horaire.objects.none()}

    # Requête de base optimisée
    related_creneaux = Creneau_Horaire.objects.select_related("cours", "personnel", "horaire")

    if user.is_sga:
        # Le SGA voit tous les horaires globaux pour le suivi du workflow
        horaires_globaux = Horaire.objects.select_related("promotion__filiere")
        context.update(
            is_sga=True,
            horaires=horaires_globaux,
            personnels=Personnel.objects.all(),
        )
    elif user.is_chef:
        # Le Chef de Filière voit :
        # 1. Les propositions de créneaux non encore intégrées à un horaire
        propositions_en_attente = related_creneaux.filter(
            status=STATUS_PROPOSED, 
            horaire__isnull=True
        )
        # 2. Les horaires globaux de sa filière (Génie Logiciel)
        horaires_integres = Horaire.objects.filter(
            promotion__filiere__nom_filiere="Génie Logiciel"
        ).select_related("promotion__filiere")
        
        context.update(
            is_chef=True, 
            horaires=horaires_integres, 
            propositions_en_attente=propositions_en_attente,
            total_propositions=propositions_en_attente.count()
        )
    elif user.is_enseignant and hasattr(request.user, "personnel"):
        enseignant_creneaux = related_creneaux.filter(personnel=request.user.personnel)
        cours = enseignant_creneaux.filter(type_horaire=TYPE_COURS)
        examens = enseignant_creneaux.filter(type_horaire=TYPE_EXAMEN)
        type_filtre_dashboard = request.GET.get("type", TYPE_COURS)
        if type_filtre_dashboard == TYPE_EXAMEN:
            creneaux_a_afficher = examens
        else:
            creneaux_a_afficher = cours

        # Statistiques pour l'enseignant
        cours_published = cours.filter(horaire__status=STATUS_PUBLISHED).count()
        cours_pending = cours.filter(
            horaire__status__in=(STATUS_PROPOSED, STATUS_CONFIRMED)
        ).count()
        examens_published = examens.filter(horaire__status=STATUS_PUBLISHED).count()
        examens_pending = examens.filter(
            horaire__status__in=(STATUS_PROPOSED, STATUS_CONFIRMED)
        ).count()

        # Disponibilités de l'enseignant
        disponibilites = Disponibilite.objects.filter(
            enseignant=request.user.personnel
        ).order_by("jour", "heure_debut")

        # Cours du jour (aujourd'hui)
        today_name = datetime.date.today().strftime("%A")
        jour_map = {
            "Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
            "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi",
        }
        today_fr = jour_map.get(today_name, "")
        cours_aujourdhui = cours.filter(jours=today_fr) if today_fr else cours.none()

        context.update(
            is_enseignant=True,
            horaires=enseignant_creneaux,
            cours=cours,
            examens=examens,
            creneaux_a_afficher=creneaux_a_afficher,
            type_filtre_dashboard=type_filtre_dashboard,
            cours_count=cours.count(),
            examens_count=examens.count(),
            cours_published=cours_published,
            cours_pending=cours_pending,
            examens_published=examens_published,
            examens_pending=examens_pending,
            disponibilites=disponibilites,
            disponibilites_count=disponibilites.count(),
            cours_aujourdhui=cours_aujourdhui,
            cours_aujourdhui_count=cours_aujourdhui.count(),
        )
    elif user.is_etudiant and hasattr(request.user, "etudiant"):
        # Pour les étudiants, on veut afficher les horaires globaux (Horaire) de leur promotion
        etudiant = request.user.etudiant
        if etudiant.promotion:
            # Récupérer les horaires globaux PUBLISHED de la promotion de l'étudiant
            horaires_globaux = Horaire.objects.filter(
                status=STATUS_PUBLISHED,
                promotion=etudiant.promotion
            ).select_related("promotion__filiere")
        else:
            horaires_globaux = Horaire.objects.filter(status=STATUS_PUBLISHED).select_related("promotion__filiere")

        context.update(
            is_etudiant=True,
            horaires=horaires_globaux,
            etudiant_promotion=etudiant.promotion
        )

    # Statistiques globales pour le dashboard
    horaires_final = context["horaires"]
    context["published_count"] = horaires_final.filter(status=STATUS_PUBLISHED).count() if not user.is_enseignant else 0
    context["pending_count"] = horaires_final.filter(
        status__in=("PROPOSED", "CONFIRMED")
    ).count() if not user.is_enseignant else 0

    # Statistiques spécifiques pour les étudiants
    if user.is_etudiant:
        context["etudiant_cours_count"] = horaires_final.filter(type_horaire=TYPE_COURS).count()
        context["etudiant_examens_count"] = horaires_final.filter(type_horaire=TYPE_EXAMEN).count()

    return render(request, "core/dashboard.html", context)


# ---------------------------------------------------------------------------
# Gestion des horaires
# ---------------------------------------------------------------------------

@login_required
def schedule_list(request):
    """Liste paginée et filtrable des horaires."""
    user = request.user
    roles = _roles(user)
    context = {"user_roles": roles}

    horaires = Creneau_Horaire.objects.select_related(
        "cours", "personnel", "horaire__promotion__filiere"
    )

    # Priorité au SGA : le SGA voit tous les créneaux pour validation
    if user.is_sga:
        context["is_sga"] = True
        # Le SGA voit tous les créneaux sans filtration
    elif user.is_enseignant and hasattr(request.user, "personnel"):
        context["is_enseignant"] = True
        horaires = horaires.filter(personnel=request.user.personnel)
    elif user.is_chef:
        context["is_chef"] = True
        # Le chef de filière ne voit que les créneaux de ses propres promotions
        # Filtrer par la filière Génie Logiciel (filière du chef)
        horaires = horaires.filter(horaire__promotion__filiere__nom_filiere="Génie Logiciel")
    elif user.is_etudiant:
        context["is_etudiant"] = True
        # Filtrer par promotion si l'étudiant est connecté
        if hasattr(request.user, "etudiant") and request.user.etudiant.promotion:
            horaires = horaires.filter(status="PUBLISHED", horaire__promotion=request.user.etudiant.promotion)
        else:
            horaires = horaires.filter(status="PUBLISHED")
    else:
        horaires = horaires.none()

    # Filtrage par statut
    status = request.GET.get("status", "")
    if status in dict(STATUS_CHOICES):
        horaires = horaires.filter(status=status)

    # Filtrage par promotion
    promotion_id = request.GET.get("promotion", "")
    if promotion_id and promotion_id.isdigit():
        horaires = horaires.filter(horaire__promotion__id_prom=promotion_id)

    # Recherche par mot-clé
    search = request.GET.get("q", "").strip()
    if search:
        horaires = (
            horaires.filter(cours__titre__icontains=search)
            | horaires.filter(personnel__nom__icontains=search)
            | horaires.filter(personnel__post_nom__icontains=search)
        ).distinct()

    # Récupérer toutes les promotions pour le filtre
    promotions = Promotion.objects.all().order_by("filiere__nom_filiere", "designation")

    context.update(active_status=status, search=search, promotions=promotions, active_promotion=promotion_id)

    # Filtrage par type (cours / examen) pour la page de gestion des créneaux
    type_filtre = request.GET.get("type_horaire", "")
    if type_filtre in (TYPE_COURS, TYPE_EXAMEN):
        horaires = horaires.filter(type_horaire=type_filtre)
    context["type_filtre"] = type_filtre
    context["TYPE_COURS"] = TYPE_COURS
    context["TYPE_EXAMEN"] = TYPE_EXAMEN

    # Pagination
    page_number = request.GET.get("page", 1)
    paginator = Paginator(horaires, PAGINATE_BY)
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj
    context["horaires"] = page_obj

    return render(request, "core/schedule_list.html", context)


@role_required(ROLE_CHEF)
def edit_schedule(request, pk=None):
    """
    Création ou édition d'un créneau horaire (Chef de Filière).
    
    Un Créneau est une proposition individuelle qui peut être :
    - Indépendante (proposition isolée)
    - Intégrée dans un Horaire global
    """
    creneau = get_object_or_404(Creneau_Horaire, pk=pk) if pk else None
    
    if creneau and creneau.status not in (STATUS_DRAFT, STATUS_PROPOSED):
        messages.error(request, "Un créneau confirmé ou publié ne peut plus être modifié.")
        return redirect("dashboard")

    form = CreneauHoraireForm(request.POST or None, instance=creneau)
    
    if request.method == "POST" and form.is_valid():
        instance = form.save(commit=False)
        
        # Gestion du statut : forcer DRAFT ou PROPOSED pour les créations/modifs du Chef
        status = request.POST.get("status")
        instance.status = status if status in (STATUS_DRAFT, STATUS_PROPOSED) else STATUS_DRAFT
        
        # Si le Chef veut l'affecter à un Horaire global, on récupère l'ID depuis le POST
        horaire_id = request.POST.get("horaire")
        if horaire_id:
            horaire = Horaire.objects.get(pk=horaire_id)
            instance.horaire = horaire
        
        instance.save()
        messages.success(request, "Créneau enregistré avec succès.")
        return redirect("dashboard")

    # Pour le formulaire, on peut ajouter la liste des Horaires disponibles pour l'affectation
    horaires_dispos = Horaire.objects.all()
    
    # Disponibilités des enseignants pour le lien visuel dans le formulaire
    import json
    from collections import defaultdict
    
    disponibilites_qs = Disponibilite.objects.select_related("enseignant").order_by(
        "enseignant", "jour", "heure_debut"
    )
    
    # Structurer les données par enseignant → jour → liste de créneaux
    dispo_data = defaultdict(lambda: defaultdict(list))
    for d in disponibilites_qs:
        teacher_id = str(d.enseignant.pk)
        dispo_data[teacher_id][d.jour].append({
            "debut": d.heure_debut.strftime("%H:%M"),
            "fin": d.heure_fin.strftime("%H:%M"),
            "note": d.note or "",
        })
    disponibilites_json = json.dumps(dispo_data)

    # Mapping cours → enseignant (basé sur les créneaux existants)
    cours_enseignant = {}
    for c in Cours.objects.all():
        creneau = Creneau_Horaire.objects.filter(cours=c).select_related("personnel").first()
        if creneau and creneau.personnel:
            cours_enseignant[str(c.pk)] = str(creneau.personnel.pk)
    cours_enseignant_json = json.dumps(cours_enseignant)

    # Propositions de l'enseignant sélectionné (pour pré-remplissage)
    # Structurer par enseignant → jour → liste de propositions
    propositions_par_enseignant_par_jour = defaultdict(lambda: defaultdict(list))
    for prop in Creneau_Horaire.objects.filter(status=STATUS_PROPOSED, horaire__isnull=True):
        teacher_id = str(prop.personnel.pk)
        jour_key = prop.jours or (prop.date.strftime("%A") if prop.date else "Inconnu")
        propositions_par_enseignant_par_jour[teacher_id][jour_key].append({
            "id": prop.pk,
            "cours": prop.cours.titre,
            "jours": prop.jours,
            "date": prop.date.strftime("%Y-%m-%d") if prop.date else None,
            "heure": prop.heure,
            "type": prop.type_horaire,
        })
    propositions_json = json.dumps(propositions_par_enseignant_par_jour)
    
    return render(request, "core/edit_schedule.html", {
        "creneau": creneau,
        "form": form,
        "horaires": horaires_dispos,
        "disponibilites_json": disponibilites_json,
        "cours_enseignant_json": cours_enseignant_json,
        "propositions_json": propositions_json,
    })


@role_required(ROLE_CHEF)
def publish_schedule(request, pk):
    """
    Publication d'un créneau horaire individuel.

    Un créneau confirmé par le SGA peut être publié.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    creneau = get_object_or_404(Creneau_Horaire, pk=pk)

    if creneau.status != STATUS_CONFIRMED:
        messages.error(request, "Seul un créneau confirmé par le SGA peut être publié.")
    else:
        creneau.status = STATUS_PUBLISHED
        creneau.save()
        messages.success(request, "Le créneau a été publié officiellement.")

    return redirect("schedule_list")


@role_required(ROLE_SGA)
def confirm_schedule(request, pk):
    """
    Confirmation d'un créneau horaire individuel par le SG-A.

    Le SG-A confirme un créneau proposé par un enseignant.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    creneau = get_object_or_404(Creneau_Horaire, pk=pk)

    if creneau.status != STATUS_PROPOSED:
        messages.error(request, "Seul un créneau proposé peut être confirmé.")
    else:
        creneau.status = STATUS_CONFIRMED
        creneau.save()
        messages.success(request, "Le créneau a été confirmé par le SGA.")

    return redirect("schedule_list")

@role_required(ROLE_SGA)
def bulk_confirm_schedules(request):
    """
    Confirmation en masse de plusieurs créneaux horaires par le SG-A.

    Le SG-A peut sélectionner plusieurs créneaux proposés et les confirmer en une seule opération.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # Récupérer les IDs des créneaux sélectionnés
    creneau_ids = request.POST.getlist('select_creneaux')
    if not creneau_ids:
        messages.error(request, "Aucun créneau sélectionné.")
        return redirect("schedule_list")

    # Confirmer chaque créneau sélectionné
    confirmed_count = 0
    for creneau_id in creneau_ids:
        try:
            creneau = Creneau_Horaire.objects.get(pk=creneau_id)
            if creneau.status == STATUS_PROPOSED:
                creneau.status = STATUS_CONFIRMED
                creneau.save()
                confirmed_count += 1
        except Creneau_Horaire.DoesNotExist:
            continue

    if confirmed_count > 0:
        messages.success(request, f"{confirmed_count} créneau(x) confirmé(s) avec succès par le SGA.")
    else:
        messages.error(request, "Aucun créneau valide à confirmer.")

    return redirect("schedule_list")


# ---------------------------------------------------------------------------
# Disponibilités
# ---------------------------------------------------------------------------

@role_required(ROLE_ENSEIGNANT)
def submit_availability(request):
    """Soumission des disponibilités d'un enseignant."""
    if not hasattr(request.user, "personnel"):
        messages.error(request, "Aucun profil personnel associé.")
        return redirect("dashboard")

    if request.method == "POST":
        rows = zip(
            request.POST.getlist("jour[]"),
            request.POST.getlist("debut[]"),
            request.POST.getlist("fin[]"),
            request.POST.getlist("note[]"),
        )
        forms = [
            DisponibiliteForm(
                {"jour": j, "heure_debut": d, "heure_fin": f, "note": n}
            )
            for j, d, f, n in rows
        ]
        if forms and all(form.is_valid() for form in forms):
            with transaction.atomic():
                for form in forms:
                    item = form.save(commit=False)
                    item.enseignant = request.user.personnel
                    item.save()
            messages.success(request, "Disponibilités soumises.")
            return redirect("dashboard")
        messages.error(request, "Corrigez les créneaux invalides.")

    disponibilites = Disponibilite.objects.filter(
        enseignant=request.user.personnel
    ).order_by("jour", "heure_debut")
    return render(request, "core/availability.html", {"disponibilites": disponibilites})


@role_required(ROLE_ENSEIGNANT)
def delete_availability(request, pk):
    """Suppression d'une disponibilité d'un enseignant."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not hasattr(request.user, "personnel"):
        messages.error(request, "Aucun profil personnel associé.")
        return redirect("dashboard")
    disponibilite = get_object_or_404(
        Disponibilite, pk=pk, enseignant=request.user.personnel
    )
    disponibilite.delete()
    messages.success(request, "Disponibilité supprimée.")
    return redirect("submit_availability")


@role_required(ROLE_ENSEIGNANT)
def teacher_courses(request):
    """Liste des cours (Cours) assignés à l'enseignant connecté, déduits des créneaux."""
    if not hasattr(request.user, "personnel"):
        messages.error(request, "Aucun profil personnel associé.")
        return redirect("dashboard")
    cours = Cours.objects.filter(
        horaires__personnel=request.user.personnel
    ).distinct().order_by("titre")
    return render(request, "core/teacher_courses.html", {"cours": cours})


@role_required(ROLE_ENSEIGNANT)
def annotate_schedule(request, pk):
    """Ajout d'une annotation à un horaire (Enseignant)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not hasattr(request.user, "personnel"):
        messages.error(request, "Aucun profil personnel associé.")
        return redirect("dashboard")
    horaire = get_object_or_404(Creneau_Horaire, pk=pk, personnel=request.user.personnel)
    horaire.annotations = request.POST.get("annotations", "").strip()
    horaire.save(update_fields=["annotations"])
    messages.success(request, "Annotation enregistrée.")
    return redirect("dashboard")


# ---------------------------------------------------------------------------
# Gestion du personnel
# ---------------------------------------------------------------------------

@role_required(ROLE_SGA)
def manage_personnel(request, pk=None):
    """Liste, création et édition du personnel (SG-A)."""
    personnel = get_object_or_404(Personnel, pk=pk) if pk else None
    form = PersonnelForm(request.POST or None, instance=personnel)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Personnel mis à jour." if personnel else "Personnel ajouté.",
        )
        return redirect("manage_personnel")

    personnels_list = Personnel.objects.all().order_by("nom", "post_nom")
    page_number = request.GET.get("page", 1)
    paginator = Paginator(personnels_list, PAGINATE_BY)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "core/personnel.html",
        {
            "form": form,
            "personnel": personnel,
            "page_obj": page_obj,
            "personnels": page_obj,
        },
    )


@role_required(ROLE_SGA)
def delete_personnel(request, pk):
    """Suppression d'un membre du personnel (SG-A)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    personnel = get_object_or_404(Personnel, pk=pk)
    if personnel.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
    else:
        try:
            personnel.delete()
            messages.success(request, "Personnel supprimé.")
        except IntegrityError:
            messages.error(
                request,
                "Suppression impossible : cet élément est encore utilisé.",
            )
    return redirect("manage_personnel")


# ---------------------------------------------------------------------------
# Gestion des référentiels (filieres, promotions, cours, fonctions)
# ---------------------------------------------------------------------------

REFERENTIELS = {
    "filieres": (Filiere, FiliereForm, "Filières", "nom_filiere"),
    "promotions": (Promotion, PromotionForm, "Promotions", "designation"),
    "cours": (Cours, CoursForm, "Cours", "titre"),
    "fonctions": (Fonction, FonctionForm, "Fonctions", "intitule"),
}


@role_required(ROLE_SGA, ROLE_CHEF)
def manage_referentiel(request, type_objet, pk=None):
    """Gestion unifiée des référentiels académiques."""
    if type_objet not in REFERENTIELS:
        return redirect("dashboard")
    model, form_class, titre, champ_nom = REFERENTIELS[type_objet]
    objet = get_object_or_404(model, pk=pk) if pk else None
    form = form_class(request.POST or None, instance=objet)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{titre.rstrip('s')} enregistré(e).")
        return redirect("manage_referentiel", type_objet=type_objet)

    objets_list = model.objects.all()
    # Filtrer les promotions pour le chef de filière (uniquement Génie Logiciel)
    if type_objet == "promotions" and request.user.is_chef:
        objets_list = objets_list.filter(filiere__nom_filiere="Génie Logiciel")
    page_number = request.GET.get("page", 1)
    paginator = Paginator(objets_list, PAGINATE_BY)
    page_obj = paginator.get_page(page_number)

    # Pour les cours, récupérer l'enseignant lié à chaque cours
    enseignants_par_cours = {}
    if type_objet == "cours":
        for cours in page_obj:
            if cours.enseignant:
                enseignants_par_cours[cours.pk] = [cours.enseignant]
            else:
                # Fallback : déduire des créneaux existants
                enseignants = Personnel.objects.filter(
                    dispense_cours__cours=cours
                ).distinct()
                enseignants_par_cours[cours.pk] = list(enseignants)

    return render(
        request,
        "core/referentiel.html",
        {
            "form": form,
            "objet": objet,
            "page_obj": page_obj,
            "objets": page_obj,
            "titre": titre,
            "type_objet": type_objet,
            "champ_nom": champ_nom,
            "user_roles": _roles(request.user),
            "enseignants_par_cours": enseignants_par_cours,
        },
    )


@role_required(ROLE_SGA, ROLE_CHEF)
def delete_referentiel(request, type_objet, pk):
    """Suppression d'un élément de référentiel."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if type_objet not in REFERENTIELS:
        return redirect("dashboard")
    model, _, titre, _ = REFERENTIELS[type_objet]
    objet = get_object_or_404(model, pk=pk)
    try:
        objet.delete()
        messages.success(request, f"{titre.rstrip('s')} supprimé(e).")
    except IntegrityError:
        messages.error(
            request,
            "Suppression impossible : cet élément est encore utilisé.",
        )
    return redirect("manage_referentiel", type_objet=type_objet)



# ---------------------------------------------------------------------------
# Gestion des étudiants
# ---------------------------------------------------------------------------

@role_required(ROLE_SGA)
def manage_students(request, pk=None):
    """Liste, inscription et édition des étudiants (SG-A)."""
    etudiant = get_object_or_404(Etudiant, pk=pk) if pk else None
    form = EtudiantForm(request.POST or None, instance=etudiant)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Étudiant enregistré.")
        return redirect("manage_students")

    etudiants_list = Etudiant.objects.select_related("promotion__filiere")
    page_number = request.GET.get("page", 1)
    paginator = Paginator(etudiants_list, PAGINATE_BY)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "core/students.html",
        {
            "form": form,
            "etudiant": etudiant,
            "page_obj": page_obj,
            "etudiants": page_obj,
            "user_roles": _roles(request.user),
            "is_sga": True,
        },
    )


@role_required(ROLE_SGA)
def delete_student(request, pk):
    """Suppression d'un étudiant (SG-A)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    get_object_or_404(Etudiant, pk=pk).delete()
    messages.success(request, "Étudiant supprimé.")
    return redirect("manage_students")


# ---------------------------------------------------------------------------
# Gestion globale des emplois du temps
# ---------------------------------------------------------------------------

@role_required(ROLE_CHEF, ROLE_SGA)
def horaire_list(request):
    """Liste des emplois du temps globaux (objets Horaire), filtrés par type et promotion."""
    user = request.user
    type_filtre = request.GET.get("type", TYPE_COURS)

    # Valider le type
    if type_filtre not in (TYPE_COURS, TYPE_EXAMEN):
        type_filtre = TYPE_COURS

    horaires = Horaire.objects.filter(type_horaire=type_filtre).select_related(
        "promotion__filiere"
    )

    if user.is_chef:
        # Le chef ne voit que les horaires de sa filière (Génie Logiciel)
        horaires = horaires.filter(promotion__filiere__nom_filiere="Génie Logiciel")

    # Filtrage par promotion
    promotion_id = request.GET.get("promotion", "")
    if promotion_id and promotion_id.isdigit():
        horaires = horaires.filter(promotion__id_prom=promotion_id)

    # Récupérer toutes les promotions pour le filtre (uniquement Génie Logiciel pour le chef)
    promotions = Promotion.objects.all().order_by("filiere__nom_filiere", "designation")
    if user.is_chef:
        promotions = promotions.filter(filiere__nom_filiere="Génie Logiciel")

    # Ajouter les rôles au contexte pour le template
    context = {
        "horaires": horaires,
        "user_roles": _roles(user),
        "is_sga": user.is_sga,
        "is_chef": user.is_chef,
        "type_filtre": type_filtre,
        "TYPE_COURS": TYPE_COURS,
        "TYPE_EXAMEN": TYPE_EXAMEN,
        "promotions": promotions,
        "active_promotion": promotion_id,
    }
    return render(request, "core/horaire_list.html", context)


@role_required(ROLE_CHEF)
def create_horaire(request):
    """Création d'un horaire global (Chef de Filière)."""
    if request.method == "POST":
        form = HoraireForm(request.POST)
        if form.is_valid():
            horaire = form.save(commit=False)
            # Par défaut, un horaire créé par le chef est en brouillon
            horaire.status = STATUS_DRAFT
            horaire.save()
            messages.success(request, "Emploi du temps créé avec succès. Vous pouvez maintenant y intégrer des créneaux.")
            return redirect("horaire_list")
    else:
        form = HoraireForm()

    return render(request, "core/create_horaire.html", {
        "form": form,
        "user_roles": _roles(request.user),
    })

@role_required(ROLE_CHEF, ROLE_SGA, ROLE_ETUDIANT)
def view_horaire(request, pk):
    """Affichage des détails d'un horaire global (Chef de Filière, SGA et Étudiant)."""
    from .models import JOURS_CHOICES
    horaire = get_object_or_404(Horaire, pk=pk)

    # Vérifier que l'étudiant ne peut voir que les horaires de sa promotion
    user = request.user
    if user.is_etudiant and hasattr(user, "etudiant"):
        if user.etudiant.promotion and horaire.promotion != user.etudiant.promotion:
            messages.error(request, "Accès refusé : vous ne pouvez voir que les horaires de votre promotion.")
            return redirect("dashboard")

    return render(request, "core/view_horaire.html", {
        "horaire": horaire,
        "user_roles": _roles(request.user),
        "jours_semaine": JOURS_CHOICES,
    })

@role_required(ROLE_CHEF, ROLE_SGA)
def edit_horaire(request, pk):
    """Édition d'un horaire global (Chef de Filière et SGA)."""
    horaire = get_object_or_404(Horaire, pk=pk)

    if request.method == "POST":
        form = HoraireForm(request.POST, instance=horaire)
        if form.is_valid():
            form.save()
            messages.success(request, "Emploi du temps mis à jour avec succès.")
            return redirect("horaire_list")
    else:
        form = HoraireForm(instance=horaire)

    return render(request, "core/edit_horaire.html", {
        "form": form,
        "horaire": horaire,
        "user_roles": _roles(request.user),
    })


@role_required(ROLE_CHEF)
def propose_horaire(request, pk):
    """
    Proposition d'un horaire global au SGA (Chef de Filière).
    Transition : DRAFT → PROPOSED
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    horaire = get_object_or_404(Horaire, pk=pk)

    if horaire.status != STATUS_DRAFT:
        messages.error(request, "Seul un horaire en brouillon peut être proposé au SGA.")
    else:
        horaire.transitionner(STATUS_PROPOSED)
        messages.success(request, f"L'horaire « {horaire.titre} » a été proposé au SGA pour validation.")

    return redirect("horaire_list")


@role_required(ROLE_SGA)
def confirm_horaire(request, pk):
    """
    Confirmation d'un horaire global par le SG-A.
    Transition : PROPOSED → CONFIRMED
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    horaire = get_object_or_404(Horaire, pk=pk)

    if horaire.status != STATUS_PROPOSED:
        messages.error(request, "Seul un horaire proposé par le Chef de Filière peut être confirmé.")
    else:
        horaire.transitionner(STATUS_CONFIRMED)
        messages.success(request, f"L'horaire « {horaire.titre} » a été confirmé par le SGA.")

    return redirect("horaire_list")


@role_required(ROLE_CHEF)
def publish_horaire(request, pk):
    """
    Publication d'un horaire global (Chef de Filière).
    Transition : CONFIRMED → PUBLISHED
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    horaire = get_object_or_404(Horaire, pk=pk)

    if horaire.status != STATUS_CONFIRMED:
        messages.error(request, "Seul un horaire confirmé par le SGA peut être publié.")
    else:
        horaire.transitionner(STATUS_PUBLISHED)
        messages.success(request, f"L'horaire « {horaire.titre} » a été publié officiellement.")

    return redirect("horaire_list")


@role_required(ROLE_CHEF)
def propositions_list(request):
    """Liste des créneaux proposés par les enseignants non encore affectés."""
    propositions = Creneau_Horaire.objects.filter(
        status=STATUS_PROPOSED,
        horaire__isnull=True
    ).select_related("cours", "personnel")

    context = {
        "propositions": propositions,
        "user_roles": _roles(request.user),
    }
    return render(request, "core/propositions_list.html", context)

@role_required(ROLE_CHEF)
def generate_promotion_horaires(request, promotion_id):
    """
    Génération des horaires de cours et d'examens pour une promotion.
    Crée uniquement les horaires manquants (2 horaires de cours et 4 horaires d'examens).
    """
    promotion = get_object_or_404(Promotion, pk=promotion_id)

    # Vérifier que la promotion appartient à la filière du chef (Génie Logiciel)
    if promotion.filiere.nom_filiere != "Génie Logiciel":
        messages.error(request, "Vous ne pouvez générer des horaires que pour les promotions de Génie Logiciel.")
        return redirect("manage_referentiel", type_objet="promotions")

    annee_academique = get_annee_academique()
    horaires_crees = 0

    # Générer les horaires de cours manquants
    cours_s1, created = Horaire.objects.get_or_create(
        promotion=promotion,
        titre=f"Semestre 1 - {annee_academique}",
        defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_COURS}
    )
    if created:
        horaires_crees += 1

    cours_s2, created = Horaire.objects.get_or_create(
        promotion=promotion,
        titre=f"Semestre 2 - {annee_academique}",
        defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_COURS}
    )
    if created:
        horaires_crees += 1

    # Générer les horaires d'examens manquants
    exam_s1_session, created = Horaire.objects.get_or_create(
        promotion=promotion,
        titre=f"Session Semestre 1 - {annee_academique}",
        defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN}
    )
    if created:
        horaires_crees += 1

    exam_s1_rattrapage, created = Horaire.objects.get_or_create(
        promotion=promotion,
        titre=f"Rattrapage Semestre 1 - {annee_academique}",
        defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN}
    )
    if created:
        horaires_crees += 1

    exam_s2_session, created = Horaire.objects.get_or_create(
        promotion=promotion,
        titre=f"Session Semestre 2 - {annee_academique}",
        defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN}
    )
    if created:
        horaires_crees += 1

    exam_s2_rattrapage, created = Horaire.objects.get_or_create(
        promotion=promotion,
        titre=f"Rattrapage Semestre 2 - {annee_academique}",
        defaults={'status': STATUS_DRAFT, 'type_horaire': TYPE_EXAMEN}
    )
    if created:
        horaires_crees += 1

    if horaires_crees > 0:
        messages.success(request, f"{horaires_crees} horaires manquants ont été créés pour la promotion {promotion.designation}.")
    else:
        messages.info(request, f"Tous les horaires existent déjà pour la promotion {promotion.designation}.")

    return redirect("manage_referentiel", type_objet="promotions")

@role_required(ROLE_CHEF)
def regenerate_promotion_horaires(request, promotion_id):
    """
    Régénération des horaires de cours et d'examens pour une promotion.
    Supprime les horaires existants et crée de nouveaux horaires vides.
    """
    promotion = get_object_or_404(Promotion, pk=promotion_id)

    # Vérifier que la promotion appartient à la filière du chef (Génie Logiciel)
    if promotion.filiere.nom_filiere != "Génie Logiciel":
        messages.error(request, "Vous ne pouvez régénérer des horaires que pour les promotions de Génie Logiciel.")
        return redirect("manage_referentiel", type_objet="promotions")

    annee_academique = get_annee_academique()

    # Supprimer les horaires existants de cette promotion
    horaires_existants = Horaire.objects.filter(promotion=promotion)
    horaires_supprimes = horaires_existants.count()
    horaires_existants.delete()

    # Créer de nouveaux horaires vides
    Horaire.objects.create(
        promotion=promotion,
        titre=f"Semestre 1 - {annee_academique}",
        status=STATUS_DRAFT,
        type_horaire=TYPE_COURS
    )

    Horaire.objects.create(
        promotion=promotion,
        titre=f"Semestre 2 - {annee_academique}",
        status=STATUS_DRAFT,
        type_horaire=TYPE_COURS
    )

    Horaire.objects.create(
        promotion=promotion,
        titre=f"Session Semestre 1 - {annee_academique}",
        status=STATUS_DRAFT,
        type_horaire=TYPE_EXAMEN
    )

    Horaire.objects.create(
        promotion=promotion,
        titre=f"Rattrapage Semestre 1 - {annee_academique}",
        status=STATUS_DRAFT,
        type_horaire=TYPE_EXAMEN
    )

    Horaire.objects.create(
        promotion=promotion,
        titre=f"Session Semestre 2 - {annee_academique}",
        status=STATUS_DRAFT,
        type_horaire=TYPE_EXAMEN
    )

    Horaire.objects.create(
        promotion=promotion,
        titre=f"Rattrapage Semestre 2 - {annee_academique}",
        status=STATUS_DRAFT,
        type_horaire=TYPE_EXAMEN
    )

    messages.success(request, f"Régénération terminée : {horaires_supprimes} horaires supprimés et 6 nouveaux horaires vides créés pour la promotion {promotion.designation}.")
    return redirect("manage_referentiel", type_objet="promotions")
