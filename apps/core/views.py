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
    ChronoHoraireForm,
    CoursForm,
    DisponibiliteForm,
    EtudiantForm,
    FiliereForm,
    FonctionForm,
    PersonnelForm,
    PromotionForm,
)
from .models import (
    Chrono_Horaire,
    Cours,
    Disponibilite,
    Etudiant,
    Filiere,
    Fonction,
    Personnel,
    Promotion,
    ROLE_CHEF,
    ROLE_ENSEIGNANT,
    ROLE_ETUDIANT,
    ROLE_SGA,
    STATUS_CHOICES,
)

# Nombre d'éléments par page pour la pagination
PAGINATE_BY = 25


def _roles(user):
    """Retourne l'ensemble des rôles de l'utilisateur (cache par requête via le modèle)."""
    return user.roles


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
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
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
    context = {"user_roles": roles, "horaires": Chrono_Horaire.objects.none()}

    # Requête de base optimisée avec select_related
    related = Chrono_Horaire.objects.select_related("cours", "personnel", "fonction")

    if user.is_sga:
        context.update(is_sga=True, horaires=related, personnels=Personnel.objects.all())
    elif user.is_chef:
        context.update(is_chef=True, horaires=related)
    elif user.is_enseignant and hasattr(request.user, "personnel"):
        context.update(
            is_enseignant=True,
            horaires=related.filter(personnel=request.user.personnel),
        )
    elif user.is_etudiant and hasattr(request.user, "etudiant"):
        # Filtrer les horaires publiés par la promotion de l'étudiant
        etudiant = request.user.etudiant
        if etudiant.promotion:
            horaires = related.filter(status="PUBLISHED", promotions=etudiant.promotion)
        else:
            horaires = related.filter(status="PUBLISHED")
        context.update(is_etudiant=True, horaires=horaires)

    # Compter les statuts en une seule requête groupée
    horaires = context["horaires"]
    context["published_count"] = horaires.filter(status="PUBLISHED").count()
    context["pending_count"] = horaires.filter(
        status__in=("PROPOSED", "CONFIRMED")
    ).count()
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

    horaires = Chrono_Horaire.objects.select_related("cours", "personnel", "fonction")

    if user.is_sga:
        context["is_sga"] = True
    elif user.is_chef:
        context["is_chef"] = True
    elif user.is_enseignant and hasattr(request.user, "personnel"):
        context["is_enseignant"] = True
        horaires = horaires.filter(personnel=request.user.personnel)
    elif user.is_etudiant:
        context["is_etudiant"] = True
        # Filtrer par promotion si l'étudiant est connecté
        if hasattr(request.user, "etudiant") and request.user.etudiant.promotion:
            horaires = horaires.filter(status="PUBLISHED", promotions=request.user.etudiant.promotion)
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
        horaires = horaires.filter(promotions__id_prom=promotion_id)

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

    # Pagination
    page_number = request.GET.get("page", 1)
    paginator = Paginator(horaires, PAGINATE_BY)
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj
    context["horaires"] = page_obj

    return render(request, "core/schedule_list.html", context)


@role_required(ROLE_CHEF)
def edit_schedule(request, pk=None):
    """Création ou édition d'un horaire (Chef de Filière)."""
    horaire = get_object_or_404(Chrono_Horaire, pk=pk) if pk else None
    if horaire and horaire.status not in ("DRAFT", "PROPOSED"):
        messages.error(request, "Un horaire confirmé ou publié ne peut plus être modifié.")
        return redirect("dashboard")
    form = ChronoHoraireForm(request.POST or None, instance=horaire)
    if request.method == "POST" and form.is_valid():
        instance = form.save(commit=False)
        status = request.POST.get("status")
        instance.status = status if status in ("DRAFT", "PROPOSED") else "DRAFT"
        instance.save()
        messages.success(request, "Horaire enregistré.")
        return redirect("dashboard")
    return render(request, "core/edit_schedule.html", {"horaire": horaire, "form": form})


@role_required(ROLE_CHEF)
def publish_schedule(request, pk):
    """Publication d'un horaire confirmé (Chef de Filière)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    horaire = get_object_or_404(Chrono_Horaire, pk=pk)
    if horaire.status != "CONFIRMED":
        messages.error(request, "Seul un horaire confirmé par le SGA peut être publié.")
    else:
        horaire.transitionner("PUBLISHED")
        messages.success(request, "Horaire publié officiellement.")
    return redirect("dashboard")


@role_required(ROLE_SGA)
def confirm_schedule(request, pk):
    """Confirmation d'un horaire proposé (SG-A)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    horaire = get_object_or_404(Chrono_Horaire, pk=pk)
    if horaire.status != "PROPOSED":
        messages.error(request, "Seul un horaire proposé peut être confirmé.")
    else:
        horaire.transitionner("CONFIRMED")
        messages.success(request, "Charge horaire confirmée par le SGA.")
    return redirect("dashboard")


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
def annotate_schedule(request, pk):
    """Ajout d'une annotation à un horaire (Enseignant)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not hasattr(request.user, "personnel"):
        messages.error(request, "Aucun profil personnel associé.")
        return redirect("dashboard")
    horaire = get_object_or_404(Chrono_Horaire, pk=pk, personnel=request.user.personnel)
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
    page_number = request.GET.get("page", 1)
    paginator = Paginator(objets_list, PAGINATE_BY)
    page_obj = paginator.get_page(page_number)

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
