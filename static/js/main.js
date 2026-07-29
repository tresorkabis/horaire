/**
 * Horaires ESFORCA - Scripts globaux
 *
 * Gere :
 *   - L'ouverture/fermeture de la barre laterale sur mobile
 *   - L'ouverture/fermeture des modaux
 *   - Le filtrage dynamique de la table du personnel
 */

(function () {
    "use strict";

    // --- Sidebar (mobile) -------------------------------------------------
    window.toggleSidebar = function () {
        var sidebar = document.getElementById("sidebar");
        var overlay = document.getElementById("overlay");
        if (sidebar && overlay) {
            sidebar.classList.toggle("-translate-x-full");
            overlay.classList.toggle("hidden");
        }
    };

    // --- Modaux -----------------------------------------------------------
    window.openModal = function (id) {
        var modal = document.getElementById(id);
        if (modal) modal.classList.remove("hidden");
    };

    window.closeModal = function (id) {
        var modal = document.getElementById(id);
        if (modal) modal.classList.add("hidden");
    };

    // --- Filtrage personnel ----------------------------------------------
    window.filterPersonnel = function () {
        var input = document.getElementById("personnel-search");
        if (!input) return;
        var q = input.value.toLowerCase();
        var rows = document.querySelectorAll(".personnel-row");
        rows.forEach(function (row) {
            row.style.display = row.innerText.toLowerCase().includes(q) ? "" : "none";
        });
    };

    // --- Fermer les modaux en cliquant a l'exterieur ----------------------
    document.addEventListener("click", function (e) {
        if (e.target.classList.contains("fixed") && e.target.classList.contains("backdrop-blur-sm")) {
            e.target.classList.add("hidden");
        }
    });
})();
