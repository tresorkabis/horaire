/**
 * Horaires ESFORCA - Gestion dynamique des disponibilites
 *
 * Permet d'ajouter et de supprimer des lignes de saisie
 * dans le formulaire de disponibilite enseignant.
 */

(function () {
    "use strict";

    var DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];

    /** Cree une nouvelle ligne de formulaire pour une disponibilite. */
    function createRow() {
        var tr = document.createElement("tr");

        // Cellule Jour
        var tdDay = document.createElement("td");
        tdDay.className = "py-4 px-6";
        var select = document.createElement("select");
        select.name = "jour[]";
        select.className = "w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 outline-none";
        DAYS.forEach(function (day) {
            var opt = document.createElement("option");
            opt.value = day;
            opt.textContent = day;
            select.appendChild(opt);
        });
        tdDay.appendChild(select);

        // Cellule Heure debut
        var tdStart = document.createElement("td");
        tdStart.className = "py-4 px-6";
        var inputStart = document.createElement("input");
        inputStart.type = "time";
        inputStart.name = "debut[]";
        inputStart.className = "w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 outline-none";
        tdStart.appendChild(inputStart);

        // Cellule Heure fin
        var tdEnd = document.createElement("td");
        tdEnd.className = "py-4 px-6";
        var inputEnd = document.createElement("input");
        inputEnd.type = "time";
        inputEnd.name = "fin[]";
        inputEnd.className = "w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 outline-none";
        tdEnd.appendChild(inputEnd);

        // Cellule Note
        var tdNote = document.createElement("td");
        tdNote.className = "py-4 px-6";
        var inputNote = document.createElement("input");
        inputNote.type = "text";
        inputNote.name = "note[]";
        inputNote.placeholder = "Ex: Sauf imprévu";
        inputNote.className = "w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 outline-none";
        tdNote.appendChild(inputNote);

        // Cellule suppression
        var tdDelete = document.createElement("td");
        tdDelete.className = "py-4 px-6 text-right text-red-400 cursor-pointer hover:text-red-600";
        tdDelete.innerHTML = '<i class="fas fa-trash"></i>';
        tdDelete.addEventListener("click", function () {
            tr.remove();
        });

        tr.appendChild(tdDay);
        tr.appendChild(tdStart);
        tr.appendChild(tdEnd);
        tr.appendChild(tdNote);
        tr.appendChild(tdDelete);

        return tr;
    }

    // --- Initialisation ---------------------------------------------------
    document.addEventListener("DOMContentLoaded", function () {
        var addBtn = document.querySelector('[onclick="addRow()"]');
        if (addBtn) {
            addBtn.onclick = function () {
                var body = document.getElementById("availability-body");
                if (body) {
                    body.appendChild(createRow());
                }
            };
        }

        // Activer la suppression sur les lignes existantes
        var body = document.getElementById("availability-body");
        if (body) {
            var deleteCells = body.querySelectorAll("td:last-child");
            deleteCells.forEach(function (cell) {
                cell.style.cursor = "pointer";
                cell.addEventListener("click", function () {
                    cell.closest("tr").remove();
                });
            });
        }
    });
})();
