"""
Arène Tactique — Style Dofus, en Python avec Tkinter.

Un combat tactique au tour par tour sur grille isométrique, inspiré du
cœur du gameplay de Dofus : Points d'Action (PA) pour lancer des sorts,
Points de Mouvement (PM) pour se déplacer, positionnement sur une
grille en damier, sorts à portée et coût variables.

Remarque honnête : Dofus est un MMO en ligne avec des milliers de
joueurs et des années de contenu développées par un studio entier —
ça ne peut évidemment pas être reproduit ici. Ce jeu reprend
fidèlement la mécanique de combat tactique (la partie la plus
caractéristique et appréciée du jeu) sous forme d'un jeu solo :
enchaînez les combats contre des monstres, gagnez de l'expérience,
montez de niveau et débloquez de nouveaux sorts.

Comme le jeu de Mémoire, un menu de démarrage (dans la même fenêtre)
permet de lancer un combat, de consulter les statistiques de votre
personnage ou les règles du jeu. Pas de sélecteur de difficulté ici :
la difficulté des combats suit naturellement le niveau de votre
personnage, qui progresse de façon persistante entre les sessions
(comme dans un vrai jeu de rôle).

Remarque technique pour les curieux : la grille est dessinée en
« isométrique » (des losanges) via une simple projection ((x-y),
(x+y)) plutôt qu'une grille carrée classique, pour retrouver le look
distinctif de Dofus — mais les déplacements restent orthogonaux
(haut/bas/gauche/droite), calculés par un simple parcours en largeur
(BFS) qui respecte les Points de Mouvement disponibles.
"""

import json
import os
import random
from collections import deque
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

# ----- Grille isométrique -----

GRILLE_COLONNES = 9
GRILLE_LIGNES = 7
TAILLE_TUILE_X = 34
TAILLE_TUILE_Y = 17

LARGEUR_CANVAS = (GRILLE_COLONNES + GRILLE_LIGNES) * TAILLE_TUILE_X
HAUTEUR_CANVAS = (GRILLE_COLONNES + GRILLE_LIGNES) * TAILLE_TUILE_Y + 40
ORIGINE_X = GRILLE_LIGNES * TAILLE_TUILE_X
ORIGINE_Y = TAILLE_TUILE_Y + 50

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

# ----- Réglages du personnage et des combats -----

PA_MAX = 6
PM_MAX = 3
PV_DEPART = 50
XP_BASE_PAR_NIVEAU = 50

PM_MAX_MONSTRE = 3
PORTEE_ATTAQUE_MONSTRE = 2

DELAI_ACTION_MONSTRE_MS = 650

TAILLE_HISTORIQUE = 10

SORTS = {
    "Flèche Magique": {"pa": 3, "portee_min": 1, "portee_max": 6, "degats": (8, 12), "effet": "degats", "niveau_requis": 1},
    "Poussée": {"pa": 3, "portee_min": 1, "portee_max": 3, "degats": (3, 5), "effet": "poussee", "niveau_requis": 1},
    "Boule de Feu": {"pa": 5, "portee_min": 2, "portee_max": 5, "degats": (15, 22), "effet": "degats", "niveau_requis": 3},
    "Soin": {"pa": 4, "portee_min": 0, "portee_max": 0, "degats": (12, 18), "effet": "soin", "niveau_requis": 5},
}

FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "arene_tactique_dofus_sauvegarde.json"
)

# ----- Palette « fantasy colorée » -----
COULEUR_FOND = "#f2e6cf"
COULEUR_TITRE = "#7a4a1e"
COULEUR_TEXTE = "#4a3423"
COULEUR_BOUTON = "#c9932f"
COULEUR_BOUTON_SURVOL = "#e0a83f"

COULEUR_CASE_CLAIRE = "#a8c97f"
COULEUR_CASE_SOMBRE = "#8fb568"
COULEUR_BORDURE_CASE = "#5c7a3d"
COULEUR_SURBRILLANCE_DEPLACEMENT = "#7fc9e8"
COULEUR_SURBRILLANCE_CIBLE = "#e85f5f"

COULEUR_JOUEUR = "#3d6fb5"
COULEUR_MONSTRE = "#8b4a2b"
COULEUR_PV_FOND = "#4a1f1f"
COULEUR_PV_PLEIN = "#7cc576"
COULEUR_PV_BAS = "#e05555"

POLICE_TITRE = ("Georgia", 22, "bold")
POLICE_SOUS_TITRE = ("Georgia", 11, "italic")
POLICE_BOUTON = ("Georgia", 11, "bold")
POLICE_INFO = ("Verdana", 10, "bold")
POLICE_TEXTE = ("Verdana", 9)

LARGEUR_BOUTON_MENU = 28

REGLES_DU_JEU = (
    "Un combat tactique au tour par tour, sur une grille isométrique, "
    "inspiré de Dofus.\n\n"
    "- PA (Points d'Action) : nécessaires pour lancer un sort.\n"
    "- PM (Points de Mouvement) : nécessaires pour se déplacer d'une "
    "case (cliquez une case en surbrillance bleue).\n"
    "- Choisissez un sort dans la liste, les cases où vous pouvez "
    "toucher un ennemi s'allument en rouge : cliquez dessus pour "
    "l'utiliser.\n"
    "- « Terminer le tour » passe le tour aux monstres, qui se "
    "rapprochent et attaquent à leur tour.\n\n"
    "Gagnez un combat pour obtenir de l'expérience et monter de "
    "niveau : votre vie maximale augmente, et de nouveaux sorts se "
    "débloquent (Boule de Feu au niveau 3, Soin au niveau 5). Les "
    "combats suivants deviennent progressivement plus difficiles."
)


# ----- Sauvegarde / chargement (fichier JSON) -----

def valeurs_par_defaut():
    return {
        "personnage": {"niveau": 1, "xp": 0, "pv_max": PV_DEPART},
        "statistiques": {"combats_gagnes": 0, "combats_perdus": 0},
        "historique": [],
    }


def charger_donnees():
    donnees = valeurs_par_defaut()
    if not os.path.exists(FICHIER_SAUVEGARDE):
        return donnees
    try:
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as fichier:
            donnees.update(json.load(fichier))
    except (json.JSONDecodeError, OSError):
        return valeurs_par_defaut()
    return donnees


def sauvegarder_donnees(donnees):
    try:
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as fichier:
            json.dump(donnees, fichier, ensure_ascii=False, indent=2)
    except OSError as erreur:
        messagebox.showwarning("Sauvegarde impossible", f"Impossible d'enregistrer la sauvegarde :\n{erreur}")


def creer_bouton(parent, texte, commande, largeur=None):
    return tk.Button(
        parent, text=texte, font=POLICE_BOUTON, command=commande,
        bg=COULEUR_BOUTON, fg="#ffffff", activebackground=COULEUR_BOUTON_SURVOL,
        activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
        width=largeur, cursor="hand2",
    )


def xp_necessaire(niveau):
    return XP_BASE_PAR_NIVEAU * niveau


def sorts_debloques(niveau):
    return [nom for nom, sort in SORTS.items() if sort["niveau_requis"] <= niveau]


def distance_manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def case_vers_ecran(gx, gy):
    x = ORIGINE_X + (gx - gy) * TAILLE_TUILE_X
    y = ORIGINE_Y + (gx + gy) * TAILLE_TUILE_Y
    return x, y


def ecran_vers_case(px, py):
    u = (px - ORIGINE_X) / TAILLE_TUILE_X
    v = (py - ORIGINE_Y) / TAILLE_TUILE_Y
    gx = round((u + v) / 2)
    gy = round((v - u) / 2)
    return gx, gy


def case_valide(gx, gy):
    return 0 <= gx < GRILLE_COLONNES and 0 <= gy < GRILLE_LIGNES


def cases_atteignables(depart, portee, occupees):
    """Parcours en largeur (BFS) : renvoie {(gx,gy): distance} pour
    toutes les cases atteignables en `portee` pas ou moins, sans
    traverser de case occupée (sauf le point de départ)."""
    distances = {depart: 0}
    file = deque([depart])
    while file:
        case = file.popleft()
        d = distances[case]
        if d >= portee:
            continue
        for dx, dy in DIRECTIONS:
            voisine = (case[0] + dx, case[1] + dy)
            if voisine in distances or not case_valide(*voisine):
                continue
            if voisine in occupees:
                continue
            distances[voisine] = d + 1
            file.append(voisine)
    return distances


def generer_monstres(niveau_combat):
    """Construit la liste des monstres pour un combat, dont la
    difficulté augmente avec le niveau du personnage."""
    nb_monstres = 1 if niveau_combat < 3 else (2 if niveau_combat < 6 else 3)
    pv = 20 + niveau_combat * 8
    degats_min = 4 + niveau_combat
    degats_max = 8 + niveau_combat * 2

    colonnes_depart = [GRILLE_COLONNES - 1, GRILLE_COLONNES - 2, GRILLE_COLONNES - 1]
    lignes_depart = [GRILLE_LIGNES // 2, GRILLE_LIGNES // 2 - 2, GRILLE_LIGNES // 2 + 2]

    monstres = []
    for i in range(nb_monstres):
        gy = max(0, min(GRILLE_LIGNES - 1, lignes_depart[i]))
        monstres.append({
            "gx": colonnes_depart[i], "gy": gy,
            "pv": pv, "pv_max": pv,
            "degats_min": degats_min, "degats_max": degats_max,
            "pm": PM_MAX_MONSTRE,
        })
    return monstres


class JeuAreneDofus:
    """Classe principale qui gère la fenêtre, les écrans et le combat tactique."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Arène Tactique — Style Dofus")
        self.fenetre.configure(bg=COULEUR_FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        self.donnees = charger_donnees()
        self.id_action_monstre = None
        self.bouton_rejouer = None
        self.bouton_menu_fin = None
        self.etat = "attente"
        self.boutons_sorts = {}

        self.cadre_menu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_jeu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_stats = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_regles = tk.Frame(self.fenetre, bg=COULEUR_FOND)

        self.construire_ecran_jeu()
        self.construire_ecran_regles()

        self.afficher_menu()

    def masquer_tous_les_ecrans(self):
        for cadre in (self.cadre_menu, self.cadre_jeu, self.cadre_stats, self.cadre_regles):
            cadre.pack_forget()

    # ----- Écran de menu -----

    def afficher_menu(self):
        for widget in self.cadre_menu.winfo_children():
            widget.destroy()
        self.masquer_tous_les_ecrans()
        self.cadre_menu.pack(padx=30, pady=20)

        personnage = self.donnees["personnage"]

        tk.Label(self.cadre_menu, text="⚔ Arène Tactique ⚔", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 2))
        tk.Label(self.cadre_menu, text="Style Dofus — combats en tour par tour", font=POLICE_SOUS_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(pady=(0, 15))

        tk.Label(
            self.cadre_menu,
            text=f"Niveau {personnage['niveau']} — XP {personnage['xp']}/{xp_necessaire(personnage['niveau'])} — PV max {personnage['pv_max']}",
            font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND,
        ).pack(pady=(0, 15))

        creer_bouton(self.cadre_menu, "⚔ Nouveau combat", self.demarrer_nouvelle_partie_depuis_menu, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "📊 Statistiques", self.afficher_statistiques, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "📖 Règles du jeu", self.afficher_regles, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "🧹 Réinitialiser le personnage", self.reinitialiser_personnage, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "🚪 Quitter", self.fenetre.destroy, LARGEUR_BOUTON_MENU).pack(pady=(4, 0))

    def demarrer_nouvelle_partie_depuis_menu(self):
        self.nouvelle_partie()
        self.afficher_ecran_jeu()

    def reinitialiser_personnage(self):
        if not messagebox.askyesno(
            "Réinitialiser le personnage",
            "Remettre votre personnage au niveau 1 et effacer les statistiques ? "
            "Cette action est irréversible.",
        ):
            return
        self.donnees = valeurs_par_defaut()
        sauvegarder_donnees(self.donnees)
        messagebox.showinfo("Réinitialisation", "Votre personnage a été réinitialisé.")

    # ----- Écran de jeu -----

    def construire_ecran_jeu(self):
        cadre_info = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_info.pack(pady=8)

        self.label_niveau = tk.Label(cadre_info, text="", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_niveau.pack(side=tk.LEFT, padx=6)
        self.label_pv = tk.Label(cadre_info, text="PV : 0/0", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_pv.pack(side=tk.LEFT, padx=6)
        self.label_pa_pm = tk.Label(cadre_info, text="PA : 0   PM : 0", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_pa_pm.pack(side=tk.LEFT, padx=6)
        self.label_tour = tk.Label(cadre_info, text="", font=POLICE_INFO, fg=COULEUR_TITRE, bg=COULEUR_FOND)
        self.label_tour.pack(side=tk.LEFT, padx=6)

        self.canvas = tk.Canvas(self.cadre_jeu, width=LARGEUR_CANVAS, height=HAUTEUR_CANVAS, bg=COULEUR_FOND, highlightthickness=0)
        self.canvas.pack(padx=10, pady=5)
        self.canvas.bind("<Button-1>", self.on_click_case)

        cadre_sorts = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_sorts.pack(pady=(0, 6))
        for nom_sort, sort in SORTS.items():
            bouton = creer_bouton(cadre_sorts, f"{nom_sort} ({sort['pa']} PA)", lambda n=nom_sort: self.selectionner_sort(n))
            bouton.pack(side=tk.LEFT, padx=3)
            self.boutons_sorts[nom_sort] = bouton

        cadre_boutons_jeu = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_boutons_jeu.pack(pady=(0, 10))
        creer_bouton(cadre_boutons_jeu, "✅ Terminer le tour", self.terminer_tour_joueur).pack(side=tk.LEFT, padx=5)
        creer_bouton(cadre_boutons_jeu, "🔄 Recommencer", self.nouvelle_partie).pack(side=tk.LEFT, padx=5)
        creer_bouton(cadre_boutons_jeu, "🏠 Menu principal", self.retour_menu_jeu).pack(side=tk.LEFT, padx=5)

    def afficher_ecran_jeu(self):
        self.masquer_tous_les_ecrans()
        self.cadre_jeu.pack(padx=10, pady=10)

    def retour_menu_jeu(self):
        self.arreter_action_monstre()
        self.etat = "attente"
        self.afficher_menu()

    # ----- Démarrage d'un combat -----

    def nouvelle_partie(self):
        self.arreter_action_monstre()
        if self.bouton_rejouer is not None:
            self.bouton_rejouer.destroy()
            self.bouton_rejouer = None
        if self.bouton_menu_fin is not None:
            self.bouton_menu_fin.destroy()
            self.bouton_menu_fin = None

        personnage = self.donnees["personnage"]
        self.joueur = {
            "gx": 0, "gy": GRILLE_LIGNES // 2,
            "pv": personnage["pv_max"], "pv_max": personnage["pv_max"],
            "pa": PA_MAX, "pm": PM_MAX,
        }
        self.monstres = generer_monstres(personnage["niveau"])
        self.sort_selectionne = None
        self.cases_surbrillance = {}

        self.etat = "combat"
        self.sous_etat = "tour_joueur"

        self.canvas.delete("all")
        self.dessiner_grille()
        self.mettre_a_jour_labels()
        self.mettre_a_jour_boutons_sorts()
        self.redessiner_dynamique()

    # ----- Rendu -----

    def dessiner_grille(self):
        for gx in range(GRILLE_COLONNES):
            for gy in range(GRILLE_LIGNES):
                x, y = case_vers_ecran(gx, gy)
                points = [x, y - TAILLE_TUILE_Y, x + TAILLE_TUILE_X, y, x, y + TAILLE_TUILE_Y, x - TAILLE_TUILE_X, y]
                couleur = COULEUR_CASE_CLAIRE if (gx + gy) % 2 == 0 else COULEUR_CASE_SOMBRE
                self.canvas.create_polygon(points, fill=couleur, outline=COULEUR_BORDURE_CASE, width=1, tags="grille")

    def dessiner_surbrillance(self):
        for (gx, gy), couleur in self.cases_surbrillance.items():
            x, y = case_vers_ecran(gx, gy)
            points = [x, y - TAILLE_TUILE_Y, x + TAILLE_TUILE_X, y, x, y + TAILLE_TUILE_Y, x - TAILLE_TUILE_X, y]
            self.canvas.create_polygon(points, fill=couleur, outline="", stipple="gray50", tags="dynamique")

    def dessiner_unite(self, unite, couleur):
        x, y = case_vers_ecran(unite["gx"], unite["gy"])
        r = 14
        self.canvas.create_oval(x - r, y - r - 6, x + r, y + r - 6, fill=couleur, outline="#2b1d12", width=2, tags="dynamique")

        ratio = max(0.0, unite["pv"] / unite["pv_max"])
        largeur_barre = 32
        x0, y0 = x - largeur_barre / 2, y - r - 22
        self.canvas.create_rectangle(x0, y0, x0 + largeur_barre, y0 + 5, fill=COULEUR_PV_FOND, outline="", tags="dynamique")
        couleur_pv = COULEUR_PV_PLEIN if ratio > 0.3 else COULEUR_PV_BAS
        if ratio > 0:
            self.canvas.create_rectangle(x0, y0, x0 + largeur_barre * ratio, y0 + 5, fill=couleur_pv, outline="", tags="dynamique")

    def redessiner_dynamique(self):
        self.canvas.delete("dynamique")
        self.dessiner_surbrillance()
        for monstre in self.monstres:
            if monstre["pv"] > 0:
                self.dessiner_unite(monstre, COULEUR_MONSTRE)
        self.dessiner_unite(self.joueur, COULEUR_JOUEUR)

    def mettre_a_jour_labels(self):
        personnage = self.donnees["personnage"]
        self.label_niveau.config(text=f"Niveau {personnage['niveau']}")
        self.label_pv.config(text=f"PV : {self.joueur['pv']}/{self.joueur['pv_max']}")
        self.label_pa_pm.config(text=f"PA : {self.joueur['pa']}   PM : {self.joueur['pm']}")
        self.label_tour.config(text="Tour : Vous" if self.sous_etat == "tour_joueur" else "Tour : Monstres")

    def mettre_a_jour_boutons_sorts(self):
        niveau = self.donnees["personnage"]["niveau"]
        debloques = sorts_debloques(niveau)
        for nom_sort, bouton in self.boutons_sorts.items():
            sort = SORTS[nom_sort]
            if nom_sort not in debloques:
                bouton.pack_forget()
                continue
            bouton.pack(side=tk.LEFT, padx=3)
            peut_lancer = self.sous_etat == "tour_joueur" and self.joueur["pa"] >= sort["pa"]
            bouton.config(state="normal" if peut_lancer else "disabled", bg=COULEUR_BOUTON if peut_lancer else "#d8c9a0")

    # ----- Sélection et lancement des sorts -----

    def selectionner_sort(self, nom_sort):
        if self.etat != "combat" or self.sous_etat != "tour_joueur":
            return
        sort = SORTS[nom_sort]
        if self.joueur["pa"] < sort["pa"]:
            return

        if sort["effet"] == "soin":
            self.lancer_sort(nom_sort, (self.joueur["gx"], self.joueur["gy"]))
            return

        self.sort_selectionne = nom_sort
        self.cases_surbrillance = {}
        depart = (self.joueur["gx"], self.joueur["gy"])
        for gx in range(GRILLE_COLONNES):
            for gy in range(GRILLE_LIGNES):
                d = distance_manhattan(depart, (gx, gy))
                if sort["portee_min"] <= d <= sort["portee_max"]:
                    self.cases_surbrillance[(gx, gy)] = COULEUR_SURBRILLANCE_CIBLE
        self.redessiner_dynamique()

    def on_click_case(self, evenement):
        if self.etat != "combat" or self.sous_etat != "tour_joueur":
            return
        case = ecran_vers_case(evenement.x, evenement.y)
        if not case_valide(*case):
            return

        if self.sort_selectionne is not None:
            if case in self.cases_surbrillance:
                self.lancer_sort(self.sort_selectionne, case)
            self.sort_selectionne = None
            self.cases_surbrillance = {}
            self.redessiner_dynamique()
            return

        occupees = {(m["gx"], m["gy"]) for m in self.monstres if m["pv"] > 0}
        atteignables = cases_atteignables((self.joueur["gx"], self.joueur["gy"]), self.joueur["pm"], occupees)
        if case in atteignables:
            self.joueur["pm"] -= atteignables[case]
            self.joueur["gx"], self.joueur["gy"] = case
            self.cases_surbrillance = {}
            self.mettre_a_jour_labels()
            self.redessiner_dynamique()
        else:
            self.afficher_deplacements_possibles()

    def afficher_deplacements_possibles(self):
        occupees = {(m["gx"], m["gy"]) for m in self.monstres if m["pv"] > 0}
        atteignables = cases_atteignables((self.joueur["gx"], self.joueur["gy"]), self.joueur["pm"], occupees)
        self.cases_surbrillance = {case: COULEUR_SURBRILLANCE_DEPLACEMENT for case in atteignables if case != (self.joueur["gx"], self.joueur["gy"])}
        self.redessiner_dynamique()

    def lancer_sort(self, nom_sort, case_cible):
        sort = SORTS[nom_sort]
        self.joueur["pa"] -= sort["pa"]

        if sort["effet"] == "soin":
            soin = random.randint(*sort["degats"])
            self.joueur["pv"] = min(self.joueur["pv_max"], self.joueur["pv"] + soin)
        else:
            monstre_cible = next((m for m in self.monstres if m["pv"] > 0 and (m["gx"], m["gy"]) == case_cible), None)
            if monstre_cible is not None:
                degats = random.randint(*sort["degats"])
                monstre_cible["pv"] = max(0, monstre_cible["pv"] - degats)
                if sort["effet"] == "poussee":
                    self.repousser(monstre_cible)

        self.mettre_a_jour_labels()
        self.mettre_a_jour_boutons_sorts()
        self.redessiner_dynamique()

        if all(m["pv"] <= 0 for m in self.monstres):
            self.terminer_combat(victoire=True)

    def repousser(self, monstre):
        dx = monstre["gx"] - self.joueur["gx"]
        dy = monstre["gy"] - self.joueur["gy"]
        direction = (0, 0)
        if abs(dx) >= abs(dy) and dx != 0:
            direction = (1 if dx > 0 else -1, 0)
        elif dy != 0:
            direction = (0, 1 if dy > 0 else -1)
        else:
            return

        occupees = {(m["gx"], m["gy"]) for m in self.monstres if m is not monstre and m["pv"] > 0}
        occupees.add((self.joueur["gx"], self.joueur["gy"]))
        for _ in range(2):
            nouvelle = (monstre["gx"] + direction[0], monstre["gy"] + direction[1])
            if case_valide(*nouvelle) and nouvelle not in occupees:
                monstre["gx"], monstre["gy"] = nouvelle
            else:
                break

    # ----- Tour des monstres -----

    def terminer_tour_joueur(self):
        if self.etat != "combat" or self.sous_etat != "tour_joueur":
            return
        self.sort_selectionne = None
        self.cases_surbrillance = {}
        self.sous_etat = "tour_monstres"
        self.mettre_a_jour_labels()
        self.mettre_a_jour_boutons_sorts()
        self.redessiner_dynamique()
        self.index_monstre_actuel = 0
        self.jouer_prochain_monstre()

    def jouer_prochain_monstre(self):
        if self.etat != "combat":
            return
        if self.index_monstre_actuel >= len(self.monstres):
            self.debuter_tour_joueur()
            return

        monstre = self.monstres[self.index_monstre_actuel]
        self.index_monstre_actuel += 1
        if monstre["pv"] > 0:
            self.executer_ia_monstre(monstre)
            self.redessiner_dynamique()
            if self.etat != "combat":
                return

        self.id_action_monstre = self.fenetre.after(DELAI_ACTION_MONSTRE_MS, self.jouer_prochain_monstre)

    def executer_ia_monstre(self, monstre):
        position_joueur = (self.joueur["gx"], self.joueur["gy"])
        distance = distance_manhattan((monstre["gx"], monstre["gy"]), position_joueur)

        if distance > PORTEE_ATTAQUE_MONSTRE:
            occupees = {(m["gx"], m["gy"]) for m in self.monstres if m is not monstre and m["pv"] > 0}
            occupees.add(position_joueur)
            atteignables = cases_atteignables((monstre["gx"], monstre["gy"]), monstre["pm"], occupees)
            if atteignables:
                meilleure_case = min(atteignables, key=lambda c: distance_manhattan(c, position_joueur))
                if distance_manhattan(meilleure_case, position_joueur) < distance:
                    monstre["gx"], monstre["gy"] = meilleure_case
            distance = distance_manhattan((monstre["gx"], monstre["gy"]), position_joueur)

        if 1 <= distance <= PORTEE_ATTAQUE_MONSTRE:
            degats = random.randint(monstre["degats_min"], monstre["degats_max"])
            self.joueur["pv"] = max(0, self.joueur["pv"] - degats)
            self.mettre_a_jour_labels()
            if self.joueur["pv"] <= 0:
                self.terminer_combat(victoire=False)

    def debuter_tour_joueur(self):
        if self.etat != "combat":
            return
        self.sous_etat = "tour_joueur"
        self.joueur["pa"] = PA_MAX
        self.joueur["pm"] = PM_MAX
        self.mettre_a_jour_labels()
        self.mettre_a_jour_boutons_sorts()

    def arreter_action_monstre(self):
        if self.id_action_monstre is not None:
            self.fenetre.after_cancel(self.id_action_monstre)
            self.id_action_monstre = None

    # ----- Fin de combat -----

    def terminer_combat(self, victoire):
        self.etat = "fin_combat"
        self.arreter_action_monstre()

        niveau_augmente = False
        xp_gagnee = 0
        personnage = self.donnees["personnage"]

        if victoire:
            xp_gagnee = 20 * len(self.monstres)
            personnage["xp"] += xp_gagnee
            while personnage["xp"] >= xp_necessaire(personnage["niveau"]):
                personnage["xp"] -= xp_necessaire(personnage["niveau"])
                personnage["niveau"] += 1
                personnage["pv_max"] += 15
                niveau_augmente = True
            self.donnees["statistiques"]["combats_gagnes"] += 1
        else:
            self.donnees["statistiques"]["combats_perdus"] += 1

        historique = self.donnees.setdefault("historique", [])
        historique.insert(0, {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "resultat": "Victoire" if victoire else "Défaite",
            "niveau": personnage["niveau"],
        })
        del historique[TAILLE_HISTORIQUE:]

        sauvegarder_donnees(self.donnees)
        self.afficher_ecran_fin(victoire, xp_gagnee, niveau_augmente)

    def afficher_ecran_fin(self, victoire, xp_gagnee, niveau_augmente):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        titre = "🏆 Victoire !" if victoire else "💀 Défaite..."

        self.canvas.create_rectangle(cx - 145, cy - 90, cx + 145, cy + 95, fill="#f2e6cf", outline=COULEUR_BOUTON, width=3, tags="dynamique")
        self.canvas.create_text(cx, cy - 55, text=titre, font=POLICE_TITRE, fill=COULEUR_TITRE, tags="dynamique")
        if victoire:
            self.canvas.create_text(cx, cy - 20, text=f"+{xp_gagnee} XP", font=POLICE_INFO, fill=COULEUR_TEXTE, tags="dynamique")
            if niveau_augmente:
                self.canvas.create_text(cx, cy + 5, text=f"🌟 Niveau {self.donnees['personnage']['niveau']} !", font=POLICE_INFO, fill=COULEUR_TITRE, tags="dynamique")
        else:
            self.canvas.create_text(cx, cy - 20, text="Vos PV sont épuisés.", font=POLICE_INFO, fill=COULEUR_TEXTE, tags="dynamique")

        self.bouton_rejouer = creer_bouton(self.canvas, "⚔ Nouveau combat", self.nouvelle_partie)
        self.canvas.create_window(cx, cy + 45, window=self.bouton_rejouer, tags="dynamique")
        self.bouton_menu_fin = creer_bouton(self.canvas, "🏠 Menu principal", self.retour_menu_jeu)
        self.canvas.create_window(cx, cy + 80, window=self.bouton_menu_fin, tags="dynamique")

    # ----- Statistiques (écran intégré à la fenêtre) -----

    def afficher_statistiques(self):
        for widget in self.cadre_stats.winfo_children():
            widget.destroy()

        creer_bouton(self.cadre_stats, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(self.cadre_stats, text="📊 Statistiques", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 10))

        personnage = self.donnees["personnage"]
        stats = self.donnees.get("statistiques", {"combats_gagnes": 0, "combats_perdus": 0})

        tk.Label(self.cadre_stats, text=f"Niveau : {personnage['niveau']}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"XP : {personnage['xp']}/{xp_necessaire(personnage['niveau'])}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"PV max : {personnage['pv_max']}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Sorts débloqués : {', '.join(sorts_debloques(personnage['niveau']))}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w", wraplength=350, justify="left").pack(fill="x", pady=(0, 10))

        tk.Label(self.cadre_stats, text=f"Combats gagnés : {stats.get('combats_gagnes', 0)}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Combats perdus : {stats.get('combats_perdus', 0)}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(0, 10))

        tk.Label(self.cadre_stats, text="🕘 Historique récent :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        zone_texte = tk.Text(self.cadre_stats, width=42, height=8, font=POLICE_TEXTE, bg="#fdf8ec", fg=COULEUR_TEXTE, relief="flat", bd=6)
        historique = self.donnees.get("historique", [])
        if historique:
            for combat in historique:
                zone_texte.insert(tk.END, f"{combat['date']} - {combat['resultat']} - niveau {combat['niveau']}\n")
        else:
            zone_texte.insert(tk.END, "Aucun combat terminé pour l'instant.")
        zone_texte.config(state="disabled")
        zone_texte.pack(pady=10)

        self.masquer_tous_les_ecrans()
        self.cadre_stats.pack(padx=20, pady=20)

    # ----- Règles du jeu (écran intégré à la fenêtre) -----

    def construire_ecran_regles(self):
        creer_bouton(self.cadre_regles, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(self.cadre_regles, text="📖 Règles du jeu", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 10))
        tk.Label(self.cadre_regles, text=REGLES_DU_JEU, justify="left", wraplength=380, font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack()

    def afficher_regles(self):
        self.masquer_tous_les_ecrans()
        self.cadre_regles.pack(padx=25, pady=20)

    # ----- Fermeture -----

    def fermer_fenetre(self):
        self.arreter_action_monstre()
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    jeu = JeuAreneDofus(fenetre_principale)
    fenetre_principale.mainloop()
