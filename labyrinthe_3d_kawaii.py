"""
Labyrinthe 3D Kawaii en Python avec Tkinter.

Un vrai petit moteur de « pseudo-3D » à la Wolfenstein 3D, entièrement
calculé à la main (technique du lancer de rayons / raycasting) et
dessiné sur un Canvas Tkinter — aucune bibliothèque 3D externe.

Vous explorez un labyrinthe généré aléatoirement, vu à la première
personne, pour ramasser toutes les gemmes kawaii puis rejoindre la
sortie (repérable sur la mini-carte en haut à gauche). Flèches Haut/Bas
pour avancer/reculer, Gauche/Droite pour tourner la tête.

Comme le jeu de Mémoire, tout se passe dans une seule fenêtre : un
menu de démarrage permet de choisir la difficulté (taille du
labyrinthe), de lancer une partie, de consulter les statistiques ou
les règles du jeu. Comme Tetris et Snake Kawaii, une vraie pause est
disponible en cours de partie (touche P ou bouton « Pause ») ; pas de
« Reprendre la partie » entre deux lancements (jeu en temps réel).

Remarque technique pour les curieux : le labyrinthe est stocké comme
une grille fine où les « cases murs » et « cases couloirs » alternent
(technique classique), généré par un parcours en profondeur aléatoire
(« recursive backtracker ») qui garantit un labyrinthe parfait : un
seul chemin possible entre deux points, sans boucle. Pour chaque
colonne de l'écran, un rayon est envoyé dans le labyrinthe (algorithme
DDA) jusqu'à toucher un mur ; plus le mur est loin, plus la tranche
verticale dessinée est courte et sombre — c'est toute l'astuce de la
fausse 3D.
"""

import json
import math
import os
import random
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

# ----- Dimensions de la fenêtre de jeu -----

LARGEUR_CANVAS = 480
HAUTEUR_CANVAS = 360

NB_RAYONS = 160                 # un rayon tous les 3px environ : bon compromis vitesse/qualité
CHAMP_DE_VISION = math.radians(62)
DISTANCE_MAX = 25.0
MAX_PAS_DDA = 64                # garde-fou pour éviter une boucle infinie

VITESSE_DEPLACEMENT = 0.07      # cases parcourues par top d'horloge
VITESSE_ROTATION = 0.045        # radians par top d'horloge
RAYON_JOUEUR = 0.2              # pour la détection de collision avec les murs
RAYON_RAMASSAGE = 0.4           # distance à laquelle on ramasse une gemme / atteint la sortie

DELAI_BOUCLE_MS = 45            # ~22 images par seconde

MUR, VIDE = "#", " "

# ----- Niveaux de difficulté : taille du labyrinthe (en cases) -----
DIFFICULTES = {
    "Facile (8x8)": {"largeur": 8, "hauteur": 8, "gemmes": 4},
    "Moyen (12x12)": {"largeur": 12, "hauteur": 12, "gemmes": 6},
    "Difficile (16x16)": {"largeur": 16, "hauteur": 16, "gemmes": 8},
}

TAILLE_HISTORIQUE = 10

# ----- Palette de couleurs « kawaii » -----
COULEUR_FOND = "#fff0f6"
COULEUR_TITRE = "#d6336c"
COULEUR_TEXTE = "#7c4a9e"
COULEUR_BOUTON = "#f48fb1"
COULEUR_BOUTON_SURVOL = "#f76fa0"

COULEUR_CIEL = "#bdeaff"
COULEUR_SOL = "#f6d9c4"
COULEUR_MUR_CLAIR = "#c9a8ff"
COULEUR_MUR_SOMBRE = "#a78bfa"
COULEUR_MUR_CARTE = "#d8bfff"
COULEUR_GEMME = "#ff6fa5"

POLICE_TITRE = ("Comic Sans MS", 22, "bold")
POLICE_SOUS_TITRE = ("Comic Sans MS", 11, "italic")
POLICE_BOUTON = ("Comic Sans MS", 12, "bold")
POLICE_INFO = ("Comic Sans MS", 11, "bold")
POLICE_TEXTE = ("Comic Sans MS", 10)

LARGEUR_BOUTON_MENU = 26

MINICARTE_TAILLE = 110
MINICARTE_MARGE = 10

FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "labyrinthe_3d_kawaii_sauvegarde.json"
)

REGLES_DU_JEU = (
    "Vous explorez un labyrinthe en pseudo-3D, vu à la première "
    "personne !\n\n"
    "- ↑ / ↓ : avancer / reculer\n"
    "- ← / → : tourner la tête\n"
    "- P : mettre en pause / reprendre\n\n"
    "Ramassez toutes les gemmes 💗 (visibles sur la mini-carte en haut "
    "à gauche), puis rejoignez la sortie 🚪. Le chronomètre tourne : "
    "essayez de battre votre record pour chaque difficulté !\n\n"
    "La mini-carte affiche tout le labyrinthe, votre position et la "
    "direction où vous regardez : n'hésitez pas à vous y fier pour "
    "vous repérer."
)


# ----- Sauvegarde / chargement (fichier JSON) -----

def valeurs_par_defaut():
    return {
        "derniere_difficulte": None,
        "records": {},
        "statistiques": {"parties_jouees": 0, "total_temps": 0},
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
    """Crée un bouton avec le style « kawaii » commun à tout le jeu."""
    return tk.Button(
        parent, text=texte, font=POLICE_BOUTON, command=commande,
        bg=COULEUR_BOUTON, fg="#ffffff", activebackground=COULEUR_BOUTON_SURVOL,
        activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
        width=largeur, cursor="hand2",
    )


def assombrir_couleur(couleur, facteur):
    """Assombrit une couleur hexadécimale (#rrggbb) : facteur=1 -> couleur
    inchangée, facteur=0 -> noir. Utilisé pour l'effet de profondeur."""
    facteur = max(0.0, min(1.0, facteur))
    r = int(int(couleur[1:3], 16) * facteur)
    v = int(int(couleur[3:5], 16) * facteur)
    b = int(int(couleur[5:7], 16) * facteur)
    return f"#{r:02x}{v:02x}{b:02x}"


# ----- Génération du labyrinthe -----

def generer_labyrinthe(largeur_cellules, hauteur_cellules):
    """Construit un labyrinthe parfait (un seul chemin entre deux cases,
    sans boucle) par parcours en profondeur aléatoire. Le résultat est
    une grille fine où les cases paires sont des murs potentiels et les
    cases impaires des couloirs (technique classique de représentation
    d'un labyrinthe cellule + murs sous forme de grille uniforme)."""
    largeur_grille = 2 * largeur_cellules + 1
    hauteur_grille = 2 * hauteur_cellules + 1
    grille = [[MUR for _ in range(largeur_grille)] for _ in range(hauteur_grille)]

    for cy in range(hauteur_cellules):
        for cx in range(largeur_cellules):
            grille[2 * cy + 1][2 * cx + 1] = VIDE

    visitees = {(0, 0)}
    pile = [(0, 0)]
    while pile:
        cx, cy = pile[-1]
        voisins = []
        for dcx, dcy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ncx, ncy = cx + dcx, cy + dcy
            if 0 <= ncx < largeur_cellules and 0 <= ncy < hauteur_cellules and (ncx, ncy) not in visitees:
                voisins.append((ncx, ncy, dcx, dcy))
        if not voisins:
            pile.pop()
            continue
        ncx, ncy, dcx, dcy = random.choice(voisins)
        grille[2 * cy + 1 + dcy][2 * cx + 1 + dcx] = VIDE
        visitees.add((ncx, ncy))
        pile.append((ncx, ncy))

    return grille


def case_est_mur(grille, x, y):
    cx, cy = int(x), int(y)
    if cy < 0 or cy >= len(grille) or cx < 0 or cx >= len(grille[0]):
        return True
    return grille[cy][cx] == MUR


def peut_se_deplacer_vers(grille, x, y, rayon=RAYON_JOUEUR):
    for dx, dy in [(-rayon, 0), (rayon, 0), (0, -rayon), (0, rayon)]:
        if case_est_mur(grille, x + dx, y + dy):
            return False
    return True


# ----- Lancer de rayons (raycasting, algorithme DDA) -----

def lancer_rayon(grille, x, y, angle):
    """Envoie un rayon depuis (x, y) dans la direction `angle` et
    renvoie (distance jusqu'au mur touché, côté touché). `cote` vaut 0
    pour un mur « vertical » (rencontré en avançant en x) et 1 pour un
    mur « horizontal » (rencontré en avançant en y) : ça sert à assombrir
    légèrement un des deux pour un effet de relief, comme dans les
    vieux jeux à la Wolfenstein 3D."""
    rayon_dx = math.cos(angle)
    rayon_dy = math.sin(angle)
    case_x, case_y = int(x), int(y)

    delta_dist_x = abs(1 / rayon_dx) if rayon_dx != 0 else 1e30
    delta_dist_y = abs(1 / rayon_dy) if rayon_dy != 0 else 1e30

    if rayon_dx < 0:
        pas_x = -1
        dist_x = (x - case_x) * delta_dist_x
    else:
        pas_x = 1
        dist_x = (case_x + 1.0 - x) * delta_dist_x

    if rayon_dy < 0:
        pas_y = -1
        dist_y = (y - case_y) * delta_dist_y
    else:
        pas_y = 1
        dist_y = (case_y + 1.0 - y) * delta_dist_y

    cote = 0
    for _ in range(MAX_PAS_DDA):
        if dist_x < dist_y:
            dist_x += delta_dist_x
            case_x += pas_x
            cote = 0
        else:
            dist_y += delta_dist_y
            case_y += pas_y
            cote = 1

        if case_y < 0 or case_y >= len(grille) or case_x < 0 or case_x >= len(grille[0]):
            return DISTANCE_MAX, cote
        if grille[case_y][case_x] == MUR:
            if cote == 0:
                distance = (case_x - x + (1 - pas_x) / 2) / rayon_dx
            else:
                distance = (case_y - y + (1 - pas_y) / 2) / rayon_dy
            return abs(distance), cote

    return DISTANCE_MAX, cote


class JeuLabyrinthe3D:
    """Classe principale qui gère la fenêtre, les écrans et le moteur de rendu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Labyrinthe 3D Kawaii")
        self.fenetre.configure(bg=COULEUR_FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        self.donnees = charger_donnees()
        self.id_boucle = None
        self.id_chrono = None
        self.bouton_rejouer = None
        self.bouton_menu_fin = None
        self.en_pause = False
        self.etat = "attente"
        self.touches = {"Up": False, "Down": False, "Left": False, "Right": False}

        difficulte_initiale = self.donnees.get("derniere_difficulte") or next(iter(DIFFICULTES))
        self.difficulte_var = tk.StringVar(value=difficulte_initiale)

        self.cadre_menu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_jeu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_stats = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_regles = tk.Frame(self.fenetre, bg=COULEUR_FOND)

        self.construire_ecran_jeu()
        self.construire_ecran_regles()

        self.fenetre.bind_all("<KeyPress-Up>", lambda e: self.definir_touche("Up", True))
        self.fenetre.bind_all("<KeyRelease-Up>", lambda e: self.definir_touche("Up", False))
        self.fenetre.bind_all("<KeyPress-Down>", lambda e: self.definir_touche("Down", True))
        self.fenetre.bind_all("<KeyRelease-Down>", lambda e: self.definir_touche("Down", False))
        self.fenetre.bind_all("<KeyPress-Left>", lambda e: self.definir_touche("Left", True))
        self.fenetre.bind_all("<KeyRelease-Left>", lambda e: self.definir_touche("Left", False))
        self.fenetre.bind_all("<KeyPress-Right>", lambda e: self.definir_touche("Right", True))
        self.fenetre.bind_all("<KeyRelease-Right>", lambda e: self.definir_touche("Right", False))
        self.fenetre.bind_all("<p>", lambda e: self.basculer_pause())
        self.fenetre.bind_all("<P>", lambda e: self.basculer_pause())

        self.afficher_menu()

    def definir_touche(self, nom, valeur):
        self.touches[nom] = valeur

    def masquer_tous_les_ecrans(self):
        for cadre in (self.cadre_menu, self.cadre_jeu, self.cadre_stats, self.cadre_regles):
            cadre.pack_forget()

    # ----- Écran de menu -----

    def afficher_menu(self):
        for widget in self.cadre_menu.winfo_children():
            widget.destroy()
        self.masquer_tous_les_ecrans()
        self.cadre_menu.pack(padx=30, pady=20)

        tk.Label(self.cadre_menu, text="✨ Labyrinthe 3D Kawaii ✨", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 2))
        tk.Label(self.cadre_menu, text="‧₊˚ Ramasse les gemmes, trouve la sortie ! ˚₊‧", font=POLICE_SOUS_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(pady=(0, 15))

        cadre_difficulte = tk.Frame(self.cadre_menu, bg=COULEUR_FOND)
        cadre_difficulte.pack(pady=(0, 10))
        tk.Label(cadre_difficulte, text="Difficulté :", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(side=tk.LEFT, padx=5)
        ttk.Combobox(
            cadre_difficulte, textvariable=self.difficulte_var, values=list(DIFFICULTES.keys()),
            state="readonly", width=14,
        ).pack(side=tk.LEFT, padx=5)

        creer_bouton(self.cadre_menu, "🎀 Nouvelle partie", self.demarrer_nouvelle_partie_depuis_menu, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "📊 Statistiques", self.afficher_statistiques, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "📖 Règles du jeu", self.afficher_regles, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "🧹 Réinitialiser les statistiques", self.reinitialiser_statistiques, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "🚪 Quitter", self.fenetre.destroy, LARGEUR_BOUTON_MENU).pack(pady=(4, 0))

    def demarrer_nouvelle_partie_depuis_menu(self):
        self.nouvelle_partie()
        self.afficher_ecran_jeu()

    def reinitialiser_statistiques(self):
        if not messagebox.askyesno(
            "Réinitialiser les statistiques",
            "Effacer tous les records, l'historique et les statistiques ? "
            "Cette action est irréversible.",
        ):
            return
        self.donnees = valeurs_par_defaut()
        sauvegarder_donnees(self.donnees)
        messagebox.showinfo("Réinitialisation", "Les statistiques ont été réinitialisées.")

    # ----- Écran de jeu -----

    def construire_ecran_jeu(self):
        cadre_info = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_info.pack(pady=10)

        self.label_difficulte_jeu = tk.Label(cadre_info, text="", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_difficulte_jeu.pack(side=tk.LEFT, padx=6)
        self.label_gemmes = tk.Label(cadre_info, text="Gemmes : 0/0", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_gemmes.pack(side=tk.LEFT, padx=6)
        self.label_temps = tk.Label(cadre_info, text="Temps : 0 s", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_temps.pack(side=tk.LEFT, padx=6)
        self.label_record = tk.Label(cadre_info, text="Record : aucun", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_record.pack(side=tk.LEFT, padx=6)

        self.canvas = tk.Canvas(self.cadre_jeu, width=LARGEUR_CANVAS, height=HAUTEUR_CANVAS, bg=COULEUR_FOND, highlightthickness=0)
        self.canvas.pack(padx=10, pady=5)

        cadre_boutons_jeu = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_boutons_jeu.pack(pady=(0, 10))
        creer_bouton(cadre_boutons_jeu, "🔄 Recommencer", self.nouvelle_partie).pack(side=tk.LEFT, padx=5)
        creer_bouton(cadre_boutons_jeu, "⏸ Pause", self.basculer_pause).pack(side=tk.LEFT, padx=5)
        creer_bouton(cadre_boutons_jeu, "🏠 Menu principal", self.retour_menu_jeu).pack(side=tk.LEFT, padx=5)

    def afficher_ecran_jeu(self):
        self.masquer_tous_les_ecrans()
        self.cadre_jeu.pack(padx=10, pady=10)

    def retour_menu_jeu(self):
        self.arreter_boucle()
        self.arreter_chrono()
        self.etat = "attente"
        self.afficher_menu()

    def mettre_a_jour_record_affiche(self):
        record = self.donnees.get("records", {}).get(self.difficulte_var.get())
        if record:
            self.label_record.config(text=f"Record : {record['meilleur_temps']} s")
        else:
            self.label_record.config(text="Record : aucun")

    # ----- Démarrage d'une partie -----

    def nouvelle_partie(self):
        self.arreter_boucle()
        self.arreter_chrono()
        if self.bouton_rejouer is not None:
            self.bouton_rejouer.destroy()
            self.bouton_rejouer = None
        if self.bouton_menu_fin is not None:
            self.bouton_menu_fin.destroy()
            self.bouton_menu_fin = None

        info = DIFFICULTES[self.difficulte_var.get()]
        self.grille = generer_labyrinthe(info["largeur"], info["hauteur"])
        self.depart_cellule = (0, 0)
        self.sortie_cellule = (info["largeur"] - 1, info["hauteur"] - 1)

        cellules_possibles = [
            (cx, cy) for cx in range(info["largeur"]) for cy in range(info["hauteur"])
            if (cx, cy) not in (self.depart_cellule, self.sortie_cellule)
        ]
        nb_gemmes = min(info["gemmes"], len(cellules_possibles))
        self.gemmes_restantes = set(random.sample(cellules_possibles, nb_gemmes))
        self.gemmes_total = len(self.gemmes_restantes)
        self.gemmes_collectees = 0

        self.joueur_x = 2 * self.depart_cellule[0] + 1 + 0.5
        self.joueur_y = 2 * self.depart_cellule[1] + 1 + 0.5
        self.angle = 0.0
        self.touches = {"Up": False, "Down": False, "Left": False, "Right": False}

        self.temps_ecoule = 0
        self.en_pause = False
        self.etat = "jeu"

        self.label_difficulte_jeu.config(text=f"Difficulté : {self.difficulte_var.get()}")
        self.label_gemmes.config(text=f"Gemmes : 0/{self.gemmes_total}")
        self.label_temps.config(text="Temps : 0 s")
        self.mettre_a_jour_record_affiche()

        self.donnees["derniere_difficulte"] = self.difficulte_var.get()
        sauvegarder_donnees(self.donnees)

        self.canvas.delete("all")
        self.dessiner_scene()
        self.demarrer_chrono()
        self.boucle_jeu()

    def basculer_pause(self):
        if self.etat != "jeu":
            return
        self.en_pause = not self.en_pause
        if self.en_pause:
            self.arreter_boucle()
            self.arreter_chrono()
            self.afficher_message_pause()
        else:
            self.effacer_message_pause()
            self.demarrer_chrono()
            self.boucle_jeu()

    def afficher_message_pause(self):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        self.id_fond_pause = self.canvas.create_rectangle(cx - 90, cy - 30, cx + 90, cy + 30, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.id_texte_pause = self.canvas.create_text(cx, cy, text="⏸ En pause", font=POLICE_INFO, fill=COULEUR_TITRE)

    def effacer_message_pause(self):
        if hasattr(self, "id_fond_pause"):
            self.canvas.delete(self.id_fond_pause)
            self.canvas.delete(self.id_texte_pause)

    # ----- Chronomètre -----

    def demarrer_chrono(self):
        self.id_chrono = self.fenetre.after(1000, self.tick_chrono)

    def arreter_chrono(self):
        if self.id_chrono is not None:
            self.fenetre.after_cancel(self.id_chrono)
            self.id_chrono = None

    def tick_chrono(self):
        self.temps_ecoule += 1
        self.label_temps.config(text=f"Temps : {self.temps_ecoule} s")
        if self.etat == "jeu" and not self.en_pause:
            self.id_chrono = self.fenetre.after(1000, self.tick_chrono)

    def arreter_boucle(self):
        if self.id_boucle is not None:
            self.fenetre.after_cancel(self.id_boucle)
            self.id_boucle = None

    # ----- Déplacement et collisions -----

    def deplacer_joueur(self):
        if self.touches["Left"]:
            self.angle -= VITESSE_ROTATION
        if self.touches["Right"]:
            self.angle += VITESSE_ROTATION

        avance = 1 if self.touches["Up"] else (-1 if self.touches["Down"] else 0)
        if avance:
            dx = math.cos(self.angle) * VITESSE_DEPLACEMENT * avance
            dy = math.sin(self.angle) * VITESSE_DEPLACEMENT * avance
            if peut_se_deplacer_vers(self.grille, self.joueur_x + dx, self.joueur_y):
                self.joueur_x += dx
            if peut_se_deplacer_vers(self.grille, self.joueur_x, self.joueur_y + dy):
                self.joueur_y += dy

    def verifier_gemmes_et_sortie(self):
        for gemme in list(self.gemmes_restantes):
            gx, gy = 2 * gemme[0] + 1 + 0.5, 2 * gemme[1] + 1 + 0.5
            if (self.joueur_x - gx) ** 2 + (self.joueur_y - gy) ** 2 < RAYON_RAMASSAGE ** 2:
                self.gemmes_restantes.discard(gemme)
                self.gemmes_collectees += 1
                self.label_gemmes.config(text=f"Gemmes : {self.gemmes_collectees}/{self.gemmes_total}")

        if not self.gemmes_restantes:
            sx, sy = 2 * self.sortie_cellule[0] + 1 + 0.5, 2 * self.sortie_cellule[1] + 1 + 0.5
            if (self.joueur_x - sx) ** 2 + (self.joueur_y - sy) ** 2 < RAYON_RAMASSAGE ** 2:
                self.terminer_partie()

    # ----- Boucle principale -----

    def boucle_jeu(self):
        if self.etat != "jeu" or self.en_pause:
            return

        self.deplacer_joueur()
        self.verifier_gemmes_et_sortie()

        if self.etat == "jeu":
            self.dessiner_scene()
            self.id_boucle = self.fenetre.after(DELAI_BOUCLE_MS, self.boucle_jeu)

    # ----- Rendu (raycasting) -----

    def dessiner_scene(self):
        self.canvas.delete("scene")
        self.canvas.delete("carte")

        self.canvas.create_rectangle(0, 0, LARGEUR_CANVAS, HAUTEUR_CANVAS / 2, fill=COULEUR_CIEL, outline=COULEUR_CIEL, tags="scene")
        self.canvas.create_rectangle(0, HAUTEUR_CANVAS / 2, LARGEUR_CANVAS, HAUTEUR_CANVAS, fill=COULEUR_SOL, outline=COULEUR_SOL, tags="scene")

        largeur_colonne = LARGEUR_CANVAS / NB_RAYONS
        for i in range(NB_RAYONS):
            angle_rayon = self.angle - CHAMP_DE_VISION / 2 + (i / NB_RAYONS) * CHAMP_DE_VISION
            distance, cote = lancer_rayon(self.grille, self.joueur_x, self.joueur_y, angle_rayon)
            distance_corrigee = max(distance * math.cos(angle_rayon - self.angle), 0.0001)

            hauteur_mur = min(HAUTEUR_CANVAS, HAUTEUR_CANVAS / distance_corrigee)
            y0 = (HAUTEUR_CANVAS - hauteur_mur) / 2
            y1 = y0 + hauteur_mur

            base = COULEUR_MUR_SOMBRE if cote == 1 else COULEUR_MUR_CLAIR
            ombre = max(0.3, 1 - distance_corrigee / 10)
            couleur = assombrir_couleur(base, ombre)

            x0 = i * largeur_colonne
            self.canvas.create_rectangle(x0, y0, x0 + largeur_colonne + 1, y1, fill=couleur, outline=couleur, tags="scene")

        self.dessiner_minicarte()

    def dessiner_minicarte(self):
        hauteur_grille = len(self.grille)
        largeur_grille = len(self.grille[0])
        echelle = MINICARTE_TAILLE / max(largeur_grille, hauteur_grille)
        dx, dy = MINICARTE_MARGE, MINICARTE_MARGE

        self.canvas.create_rectangle(
            dx - 4, dy - 4, dx + largeur_grille * echelle + 4, dy + hauteur_grille * echelle + 4,
            fill="#fff8fb", outline=COULEUR_BOUTON, width=2, tags="carte",
        )

        for gy in range(hauteur_grille):
            for gx in range(largeur_grille):
                if self.grille[gy][gx] == MUR:
                    x0, y0 = dx + gx * echelle, dy + gy * echelle
                    self.canvas.create_rectangle(x0, y0, x0 + echelle, y0 + echelle, fill=COULEUR_MUR_CARTE, outline="", tags="carte")

        for gemme in self.gemmes_restantes:
            fx, fy = 2 * gemme[0] + 1 + 0.5, 2 * gemme[1] + 1 + 0.5
            x, y = dx + fx * echelle, dy + fy * echelle
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=COULEUR_GEMME, outline="", tags="carte")

        sfx, sfy = 2 * self.sortie_cellule[0] + 1 + 0.5, 2 * self.sortie_cellule[1] + 1 + 0.5
        sx, sy = dx + sfx * echelle, dy + sfy * echelle
        self.canvas.create_text(sx, sy, text="🚪", font=("Arial", 9), tags="carte")

        jx, jy = dx + self.joueur_x * echelle, dy + self.joueur_y * echelle
        self.canvas.create_oval(jx - 3, jy - 3, jx + 3, jy + 3, fill=COULEUR_TITRE, outline="", tags="carte")
        bx, by = jx + math.cos(self.angle) * 9, jy + math.sin(self.angle) * 9
        self.canvas.create_line(jx, jy, bx, by, fill=COULEUR_TITRE, width=2, tags="carte")

    # ----- Fin de partie -----

    def terminer_partie(self):
        self.etat = "fin"
        self.arreter_boucle()
        self.arreter_chrono()

        difficulte = self.difficulte_var.get()
        records = self.donnees.setdefault("records", {})
        record = records.get(difficulte)
        self.dernier_resultat_est_record = False
        if record is None or self.temps_ecoule < record["meilleur_temps"]:
            records[difficulte] = {"meilleur_temps": self.temps_ecoule}
            self.dernier_resultat_est_record = True

        stats = self.donnees.setdefault("statistiques", {"parties_jouees": 0, "total_temps": 0})
        stats["parties_jouees"] += 1
        stats["total_temps"] += self.temps_ecoule

        historique = self.donnees.setdefault("historique", [])
        historique.insert(0, {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "difficulte": difficulte,
            "temps": self.temps_ecoule,
        })
        del historique[TAILLE_HISTORIQUE:]

        sauvegarder_donnees(self.donnees)
        self.afficher_ecran_fin()

    def afficher_ecran_fin(self):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        self.canvas.create_rectangle(cx - 140, cy - 90, cx + 140, cy + 95, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.canvas.create_text(cx, cy - 60, text="🎉 Labyrinthe terminé !", font=POLICE_INFO, fill=COULEUR_TITRE)
        self.canvas.create_text(cx, cy - 30, text=f"Temps : {self.temps_ecoule} s", font=POLICE_TITRE, fill=COULEUR_TEXTE)
        if self.dernier_resultat_est_record:
            self.canvas.create_text(cx, cy, text="🌟 Nouveau record !", font=POLICE_INFO, fill=COULEUR_TITRE)

        self.bouton_rejouer = creer_bouton(self.canvas, "🔄 Rejouer", self.nouvelle_partie)
        self.canvas.create_window(cx, cy + 40, window=self.bouton_rejouer)
        self.bouton_menu_fin = creer_bouton(self.canvas, "🏠 Menu principal", self.retour_menu_jeu)
        self.canvas.create_window(cx, cy + 75, window=self.bouton_menu_fin)

    # ----- Statistiques (écran intégré à la fenêtre) -----

    def afficher_statistiques(self):
        for widget in self.cadre_stats.winfo_children():
            widget.destroy()

        creer_bouton(self.cadre_stats, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(self.cadre_stats, text="📊 Statistiques", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 10))

        stats = self.donnees.get("statistiques", {"parties_jouees": 0, "total_temps": 0})
        parties = stats.get("parties_jouees", 0)
        moyenne = stats["total_temps"] / parties if parties else 0

        tk.Label(self.cadre_stats, text=f"Labyrinthes terminés : {parties}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Temps moyen : {moyenne:.1f} s", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(0, 10))

        tk.Label(self.cadre_stats, text="🏆 Records par difficulté :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        records = self.donnees.get("records", {})
        if records:
            for difficulte, record in records.items():
                tk.Label(
                    self.cadre_stats, text=f"{difficulte} : {record['meilleur_temps']} s",
                    font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w",
                ).pack(fill="x", padx=15)
        else:
            tk.Label(self.cadre_stats, text="Aucun record pour l'instant", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", padx=15)

        tk.Label(self.cadre_stats, text="🕘 Historique récent :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(10, 0))
        zone_texte = tk.Text(self.cadre_stats, width=42, height=10, font=POLICE_TEXTE, bg="#fff8fb", fg=COULEUR_TEXTE, relief="flat", bd=6)
        historique = self.donnees.get("historique", [])
        if historique:
            for partie in historique:
                zone_texte.insert(tk.END, f"{partie['date']} - {partie['difficulte']} - {partie['temps']} s\n")
        else:
            zone_texte.insert(tk.END, "Aucune partie terminée pour l'instant.")
        zone_texte.config(state="disabled")
        zone_texte.pack(pady=10)

        self.masquer_tous_les_ecrans()
        self.cadre_stats.pack(padx=20, pady=20)

    # ----- Règles du jeu (écran intégré à la fenêtre) -----

    def construire_ecran_regles(self):
        creer_bouton(self.cadre_regles, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(self.cadre_regles, text="📖 Règles du jeu", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 10))
        tk.Label(self.cadre_regles, text=REGLES_DU_JEU, justify="left", wraplength=360, font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack()

    def afficher_regles(self):
        self.masquer_tous_les_ecrans()
        self.cadre_regles.pack(padx=25, pady=20)

    # ----- Fermeture -----

    def fermer_fenetre(self):
        self.arreter_boucle()
        self.arreter_chrono()
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    jeu = JeuLabyrinthe3D(fenetre_principale)
    fenetre_principale.mainloop()
