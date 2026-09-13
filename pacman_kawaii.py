"""
Pac-Man Kawaii en Python avec Tkinter.

Un petit Pac-Man tout rond doit manger toutes les gommes d'un
labyrinthe en évitant des fantômes pastel. Les grosses « super-gommes »
rendent les fantômes peureux quelques secondes : on peut alors les
manger pour gagner un gros bonus de points !

Comme le jeu de Mémoire, tout se passe dans une seule fenêtre : un
menu de démarrage permet de lancer une partie, de consulter les
statistiques ou les règles du jeu.

Remarque : contrairement au jeu de Mémoire, il n'y a pas de bouton
« Reprendre la partie ». Pac-Man est un jeu en temps réel (l'oiseau...
pardon, les fantômes continuent de bouger en permanence), donc mettre
une partie en pause pour la reprendre après avoir fermé le jeu n'aurait
pas beaucoup de sens : on relance simplement une nouvelle partie.

Petite musique de fond en boucle (bouton pour la couper dans le menu).
Nécessite la bibliothèque pygame (pip install pygame) ; sans elle, le
jeu fonctionne normalement, juste sans musique.
"""

import json
import os
import random
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

# La musique est optionnelle : si pygame n'est pas installé (pip install
# pygame), le jeu fonctionne quand même, simplement sans musique.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
try:
    import pygame
    pygame.mixer.init()
    MUSIQUE_DISPONIBLE = True
except Exception:
    MUSIQUE_DISPONIBLE = False

# ----- Dimensions du labyrinthe -----

TAILLE_CASE = 24
COLONNES = 19
LIGNES = 15
LARGEUR_CANVAS = COLONNES * TAILLE_CASE
HAUTEUR_CANVAS = LIGNES * TAILLE_CASE

CENTRE_LIGNE = LIGNES // 2
CENTRE_COLONNE = COLONNES // 2

# Symboles utilisés pour représenter le contenu de chaque case.
MUR, VIDE, POINT, SUPER_POINT = "#", " ", ".", "o"

JOUEUR_SPAWN = (LIGNES - 3, CENTRE_COLONNE)
FANTOME_SPAWNS = [
    (CENTRE_LIGNE, CENTRE_COLONNE - 1),
    (CENTRE_LIGNE, CENTRE_COLONNE),
    (CENTRE_LIGNE, CENTRE_COLONNE + 1),
]
COULEURS_FANTOMES = ["#ffb3c6", "#a0e7e5", "#ffd59e"]

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # haut, bas, gauche, droite
ANGLES_DIRECTION = {(0, 1): 0, (0, -1): 180, (-1, 0): 90, (1, 0): 270}

# ----- Réglages de la partie -----

VITESSE_JOUEUR = 0.09     # cases parcourues par le joueur à chaque top de la boucle
VITESSE_FANTOME = 0.075
VITESSE_FANTOME_PEUR = 0.05

DELAI_BOUCLE_MS = 40      # ~25 images par seconde
DUREE_PEUR_TICKS = int(7000 / DELAI_BOUCLE_MS)  # les fantômes ont peur pendant ~7 secondes

POINTS_POINT = 10
POINTS_SUPER_POINT = 50
POINTS_FANTOME = 200

NB_VIES_DEPART = 3
TAILLE_HISTORIQUE = 10

# ----- Palette de couleurs « kawaii » -----
COULEUR_FOND = "#fff0f6"
COULEUR_TITRE = "#d6336c"
COULEUR_TEXTE = "#7c4a9e"
COULEUR_BOUTON = "#f48fb1"
COULEUR_BOUTON_SURVOL = "#f76fa0"

COULEUR_MUR = "#c9a8ff"
COULEUR_MUR_BORD = "#a78bfa"
COULEUR_POINT = "#f8a5c2"
COULEUR_SUPER_POINT = "#ff6fa5"
COULEUR_PACMAN = "#ffe066"
COULEUR_FANTOME_PEUR = "#cfe8ff"

POLICE_TITRE = ("Comic Sans MS", 22, "bold")
POLICE_SOUS_TITRE = ("Comic Sans MS", 11, "italic")
POLICE_BOUTON = ("Comic Sans MS", 12, "bold")
POLICE_INFO = ("Comic Sans MS", 11, "bold")
POLICE_TEXTE = ("Comic Sans MS", 10)

LARGEUR_BOUTON_MENU = 26

FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pacman_kawaii_sauvegarde.json"
)

# Petite mélodie chiptune en boucle, propre à ce jeu.
FICHIER_MUSIQUE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pacman.wav"
)

REGLES_DU_JEU = (
    "Dirigez votre petit Pac-Man avec les flèches du clavier ↑ ↓ ← →.\n\n"
    "- Mangez toutes les petites gommes roses pour gagner des points.\n"
    "- Les grosses super-gommes rendent les fantômes peureux pendant "
    "quelques secondes : vous pouvez alors les manger pour un gros "
    "bonus de points !\n"
    "- Si un fantôme normal vous touche, vous perdez une vie.\n"
    "- Vous avez 3 vies. La partie se termine quand vous les perdez "
    "toutes, ou quand vous avez mangé toutes les gommes du labyrinthe.\n"
    "- Astuce : un tunnel sur le côté du labyrinthe permet de "
    "réapparaître de l'autre côté !"
)


# ----- Sauvegarde / chargement (fichier JSON) -----

def valeurs_par_defaut():
    return {
        "meilleur_score": 0,
        "statistiques": {"parties_jouees": 0, "victoires": 0, "total_score": 0},
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


def demarrer_musique():
    """Lance la musique de fond en boucle (silencieux si pygame n'est
    pas installé ou si le fichier audio est introuvable)."""
    if not MUSIQUE_DISPONIBLE:
        return
    try:
        pygame.mixer.music.load(FICHIER_MUSIQUE)
        pygame.mixer.music.play(loops=-1)
    except Exception:
        pass


def creer_bouton(parent, texte, commande, largeur=None):
    """Crée un bouton avec le style « kawaii » commun à tout le jeu."""
    return tk.Button(
        parent, text=texte, font=POLICE_BOUTON, command=commande,
        bg=COULEUR_BOUTON, fg="#ffffff", activebackground=COULEUR_BOUTON_SURVOL,
        activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
        width=largeur, cursor="hand2",
    )


def generer_labyrinthe():
    """Construit le labyrinthe : un bord de murs, des piliers intérieurs
    espacés (qui garantissent que tous les couloirs restent reliés
    entre eux), une petite maison pour les fantômes au centre, un
    tunnel horizontal et quatre super-gommes dans les coins."""
    grille = [
        [MUR if (l == 0 or l == LIGNES - 1 or c == 0 or c == COLONNES - 1) else POINT for c in range(COLONNES)]
        for l in range(LIGNES)
    ]

    for l in range(2, LIGNES - 2, 2):
        for c in range(2, COLONNES - 2, 2):
            grille[l][c] = MUR

    for l in range(CENTRE_LIGNE - 1, CENTRE_LIGNE + 2):
        for c in range(CENTRE_COLONNE - 2, CENTRE_COLONNE + 3):
            grille[l][c] = VIDE

    grille[CENTRE_LIGNE][0] = VIDE
    grille[CENTRE_LIGNE][COLONNES - 1] = VIDE

    for l, c in [(1, 1), (1, COLONNES - 2), (LIGNES - 2, 1), (LIGNES - 2, COLONNES - 2)]:
        grille[l][c] = SUPER_POINT

    return grille


class JeuPacman:
    """Classe principale qui gère la fenêtre, les écrans et la logique du jeu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Pac-Man Kawaii")
        self.fenetre.configure(bg=COULEUR_FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        self.donnees = charger_donnees()
        self.id_boucle = None
        self.bouton_rejouer = None
        self.bouton_menu_fin = None
        self.etat = "attente"

        self.cadre_menu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_jeu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_stats = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_regles = tk.Frame(self.fenetre, bg=COULEUR_FOND)

        self.musique_active = MUSIQUE_DISPONIBLE
        demarrer_musique()

        self.construire_ecran_jeu()
        self.construire_ecran_regles()

        self.fenetre.bind_all("<Up>", lambda evenement: self.touche_pressee((-1, 0)))
        self.fenetre.bind_all("<Down>", lambda evenement: self.touche_pressee((1, 0)))
        self.fenetre.bind_all("<Left>", lambda evenement: self.touche_pressee((0, -1)))
        self.fenetre.bind_all("<Right>", lambda evenement: self.touche_pressee((0, 1)))

        self.afficher_menu()

    def masquer_tous_les_ecrans(self):
        for cadre in (self.cadre_menu, self.cadre_jeu, self.cadre_stats, self.cadre_regles):
            cadre.pack_forget()

    def basculer_musique(self):
        if not MUSIQUE_DISPONIBLE:
            return
        self.musique_active = not self.musique_active
        pygame.mixer.music.set_volume(1.0 if self.musique_active else 0.0)
        if hasattr(self, "bouton_musique"):
            self.bouton_musique.config(text="🔊 Musique" if self.musique_active else "🔇 Musique")

    # ----- Écran de menu -----

    def afficher_menu(self):
        for widget in self.cadre_menu.winfo_children():
            widget.destroy()
        self.masquer_tous_les_ecrans()
        self.cadre_menu.pack(padx=30, pady=20)

        tk.Label(self.cadre_menu, text="✨ Pac-Man Kawaii ✨", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 2))
        tk.Label(self.cadre_menu, text="‧₊˚ Mange toutes les gommes ! ˚₊‧", font=POLICE_SOUS_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(pady=(0, 15))

        creer_bouton(self.cadre_menu, "🎀 Nouvelle partie", self.demarrer_nouvelle_partie_depuis_menu, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "📊 Statistiques", self.afficher_statistiques, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "📖 Règles du jeu", self.afficher_regles, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "🧹 Réinitialiser les statistiques", self.reinitialiser_statistiques, LARGEUR_BOUTON_MENU).pack(pady=4)

        texte_musique = "🔊 Musique" if self.musique_active else "🔇 Musique"
        self.bouton_musique = creer_bouton(self.cadre_menu, texte_musique, self.basculer_musique, LARGEUR_BOUTON_MENU)
        self.bouton_musique.pack(pady=4)
        if not MUSIQUE_DISPONIBLE:
            self.bouton_musique.config(state="disabled", bg="#f6c9db", text="🔇 Musique (pygame requis)")

        creer_bouton(self.cadre_menu, "🚪 Quitter", self.fenetre.destroy, LARGEUR_BOUTON_MENU).pack(pady=(4, 0))

    def demarrer_nouvelle_partie_depuis_menu(self):
        self.nouvelle_partie()
        self.afficher_ecran_jeu()

    def reinitialiser_statistiques(self):
        if not messagebox.askyesno(
            "Réinitialiser les statistiques",
            "Effacer le meilleur score, l'historique et les statistiques ? "
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

        self.label_score = tk.Label(cadre_info, text="Score : 0", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_score.pack(side=tk.LEFT, padx=10)

        self.label_vies = tk.Label(cadre_info, text="❤❤❤", font=POLICE_INFO, fg=COULEUR_TITRE, bg=COULEUR_FOND)
        self.label_vies.pack(side=tk.LEFT, padx=10)

        self.label_meilleur = tk.Label(cadre_info, text="Meilleur score : 0", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_meilleur.pack(side=tk.LEFT, padx=10)

        self.canvas = tk.Canvas(self.cadre_jeu, width=LARGEUR_CANVAS, height=HAUTEUR_CANVAS, bg=COULEUR_FOND, highlightthickness=0)
        self.canvas.pack(padx=10, pady=5)

        cadre_boutons_jeu = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_boutons_jeu.pack(pady=(0, 10))
        creer_bouton(cadre_boutons_jeu, "🔄 Recommencer", self.nouvelle_partie).pack(side=tk.LEFT, padx=5)
        creer_bouton(cadre_boutons_jeu, "🏠 Menu principal", self.retour_menu_jeu).pack(side=tk.LEFT, padx=5)

    def afficher_ecran_jeu(self):
        self.masquer_tous_les_ecrans()
        self.cadre_jeu.pack(padx=10, pady=10)

    def retour_menu_jeu(self):
        if self.id_boucle is not None:
            self.fenetre.after_cancel(self.id_boucle)
            self.id_boucle = None
        self.etat = "attente"
        self.afficher_menu()

    # ----- Démarrage d'une partie -----

    def dessiner_labyrinthe(self):
        self.ids_cellules = {}
        for l in range(LIGNES):
            for c in range(COLONNES):
                x0, y0 = c * TAILLE_CASE, l * TAILLE_CASE
                x1, y1 = x0 + TAILLE_CASE, y0 + TAILLE_CASE
                cellule = self.grille[l][c]
                if cellule == MUR:
                    self.canvas.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, fill=COULEUR_MUR, outline=COULEUR_MUR_BORD, width=2)
                elif cellule == POINT:
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    self.ids_cellules[(l, c)] = self.canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=COULEUR_POINT, outline="")
                elif cellule == SUPER_POINT:
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    self.ids_cellules[(l, c)] = self.canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=COULEUR_SUPER_POINT, outline="#ffffff", width=2)

    def creer_fantomes(self):
        fantomes = []
        for (l, c), couleur in zip(FANTOME_SPAWNS, COULEURS_FANTOMES):
            fantomes.append({
                "ligne": float(l), "colonne": float(c), "origine": (float(l), float(c)),
                "direction": (0, 0), "direction_voulue": (0, 0),
                "etat": "normal", "compteur_peur": 0, "couleur": couleur, "ids": [],
            })
        return fantomes

    def nouvelle_partie(self):
        if self.id_boucle is not None:
            self.fenetre.after_cancel(self.id_boucle)
            self.id_boucle = None
        if self.bouton_rejouer is not None:
            self.bouton_rejouer.destroy()
            self.bouton_rejouer = None
        if self.bouton_menu_fin is not None:
            self.bouton_menu_fin.destroy()
            self.bouton_menu_fin = None

        self.canvas.delete("all")
        self.grille = generer_labyrinthe()
        ligne_depart, colonne_depart = JOUEUR_SPAWN
        self.grille[ligne_depart][colonne_depart] = VIDE  # pas de gomme sous le point de départ
        self.dessiner_labyrinthe()

        self.joueur = {
            "ligne": float(ligne_depart), "colonne": float(colonne_depart),
            "direction": (0, 0), "direction_voulue": (0, 0),
        }
        self.dernier_angle = 0
        self.angle_bouche = 0
        self.ids_pacman = []

        self.fantomes = self.creer_fantomes()

        self.score = 0
        self.vies = NB_VIES_DEPART
        self.label_score.config(text="Score : 0")
        self.label_vies.config(text="❤" * self.vies)
        self.label_meilleur.config(text=f"Meilleur score : {self.donnees.get('meilleur_score', 0)}")

        self.etat = "jeu"
        self.dessiner_pacman()
        for fantome in self.fantomes:
            self.dessiner_fantome(fantome)
        self.boucle_jeu()

    # ----- Entrées du joueur -----

    def touche_pressee(self, direction):
        if self.etat == "jeu":
            self.joueur["direction_voulue"] = direction

    # ----- Déplacement générique (joueur ou fantôme) -----

    def peut_aller(self, ligne, colonne, direction):
        dl, dc = direction
        nl, nc = ligne + dl, colonne + dc
        if nc < 0 or nc >= COLONNES:
            return True  # sortie par le tunnel
        if nl < 0 or nl >= LIGNES:
            return False
        return self.grille[nl][nc] != MUR

    def deplacer_entite(self, entite, vitesse):
        l_entier = round(entite["ligne"])
        c_entier = round(entite["colonne"])
        epsilon = max(vitesse * 0.6, 0.02)
        proche_du_centre = abs(entite["ligne"] - l_entier) < epsilon and abs(entite["colonne"] - c_entier) < epsilon

        if proche_du_centre:
            entite["ligne"], entite["colonne"] = float(l_entier), float(c_entier)
            voulue = entite["direction_voulue"]
            if voulue != (0, 0) and self.peut_aller(l_entier, c_entier, voulue):
                entite["direction"] = voulue
            elif entite["direction"] != (0, 0) and not self.peut_aller(l_entier, c_entier, entite["direction"]):
                entite["direction"] = (0, 0)

        dl, dc = entite["direction"]
        entite["ligne"] += dl * vitesse
        entite["colonne"] += dc * vitesse

        if entite["colonne"] < -0.5:
            entite["colonne"] = COLONNES - 0.5
        elif entite["colonne"] > COLONNES - 0.5:
            entite["colonne"] = -0.5

    # ----- Intelligence (très simple) des fantômes -----

    def ia_fantome(self, fantome):
        l_entier = round(fantome["ligne"])
        c_entier = round(fantome["colonne"])
        epsilon = max(VITESSE_FANTOME * 0.6, 0.02)
        proche_du_centre = abs(fantome["ligne"] - l_entier) < epsilon and abs(fantome["colonne"] - c_entier) < epsilon
        if not proche_du_centre:
            return

        directions_possibles = [
            d for d in DIRECTIONS
            if d != (-fantome["direction"][0], -fantome["direction"][1]) and self.peut_aller(l_entier, c_entier, d)
        ]
        if not directions_possibles:
            directions_possibles = [d for d in DIRECTIONS if self.peut_aller(l_entier, c_entier, d)]
        if not directions_possibles:
            fantome["direction_voulue"] = (0, 0)
            return

        if fantome["etat"] == "peur" or random.random() > 0.6:
            fantome["direction_voulue"] = random.choice(directions_possibles)
        else:
            fantome["direction_voulue"] = min(
                directions_possibles,
                key=lambda d: (l_entier + d[0] - self.joueur["ligne"]) ** 2 + (c_entier + d[1] - self.joueur["colonne"]) ** 2,
            )

    # ----- Dessin de Pac-Man et des fantômes -----

    def dessiner_pacman(self):
        for identifiant in self.ids_pacman:
            self.canvas.delete(identifiant)

        x = self.joueur["colonne"] * TAILLE_CASE + TAILLE_CASE / 2
        y = self.joueur["ligne"] * TAILLE_CASE + TAILLE_CASE / 2
        r = TAILLE_CASE / 2 - 2

        self.angle_bouche = (self.angle_bouche + 4) % 40
        ouverture = abs(20 - self.angle_bouche) / 2  # la bouche s'ouvre et se ferme doucement

        angle_direction = ANGLES_DIRECTION.get(self.joueur["direction"], self.dernier_angle)
        self.dernier_angle = angle_direction

        corps = self.canvas.create_arc(
            x - r, y - r, x + r, y + r,
            start=angle_direction + ouverture, extent=360 - 2 * ouverture,
            fill=COULEUR_PACMAN, outline="", style=tk.PIESLICE,
        )
        oeil = self.canvas.create_oval(x - 2, y - r + 3, x + 2, y - r + 7, fill=COULEUR_TEXTE, outline="")
        self.ids_pacman = [corps, oeil]

    def dessiner_fantome(self, fantome):
        for identifiant in fantome["ids"]:
            self.canvas.delete(identifiant)

        x = fantome["colonne"] * TAILLE_CASE + TAILLE_CASE / 2
        y = fantome["ligne"] * TAILLE_CASE + TAILLE_CASE / 2
        r = TAILLE_CASE / 2 - 2

        if fantome["etat"] == "peur":
            if fantome["compteur_peur"] > 40 or (fantome["compteur_peur"] // 5) % 2 == 0:
                couleur = COULEUR_FANTOME_PEUR
            else:
                couleur = "#ffffff"
        else:
            couleur = fantome["couleur"]

        dome = self.canvas.create_arc(x - r, y - r, x + r, y + r, start=0, extent=180, fill=couleur, outline="")
        corps = self.canvas.create_rectangle(x - r, y, x + r, y + r - 4, fill=couleur, outline="")
        vagues = self.canvas.create_polygon(
            x - r, y + r - 4, x - r / 2, y + r + 2, x, y + r - 4, x + r / 2, y + r + 2, x + r, y + r - 4,
            fill=couleur, outline="",
        )
        oeil_g = self.canvas.create_oval(x - r * 0.5 - 3, y - 4, x - r * 0.5 + 3, y + 2, fill="#ffffff", outline="")
        oeil_d = self.canvas.create_oval(x + r * 0.5 - 3, y - 4, x + r * 0.5 + 3, y + 2, fill="#ffffff", outline="")
        pupille_g = self.canvas.create_oval(x - r * 0.5 - 1, y - 2, x - r * 0.5 + 1, y, fill=COULEUR_TEXTE, outline="")
        pupille_d = self.canvas.create_oval(x + r * 0.5 - 1, y - 2, x + r * 0.5 + 1, y, fill=COULEUR_TEXTE, outline="")

        fantome["ids"] = [dome, corps, vagues, oeil_g, oeil_d, pupille_g, pupille_d]

    # ----- Gommes et collisions -----

    def plus_aucun_point(self):
        return not any(cellule in (POINT, SUPER_POINT) for ligne in self.grille for cellule in ligne)

    def gerer_manger(self):
        l = round(self.joueur["ligne"])
        c = round(self.joueur["colonne"])
        if abs(self.joueur["ligne"] - l) > 0.1 or abs(self.joueur["colonne"] - c) > 0.1:
            return

        cellule = self.grille[l][c]
        if cellule == POINT:
            self.grille[l][c] = VIDE
            self.canvas.delete(self.ids_cellules.pop((l, c)))
            self.score += POINTS_POINT
        elif cellule == SUPER_POINT:
            self.grille[l][c] = VIDE
            self.canvas.delete(self.ids_cellules.pop((l, c)))
            self.score += POINTS_SUPER_POINT
            for fantome in self.fantomes:
                fantome["etat"] = "peur"
                fantome["compteur_peur"] = DUREE_PEUR_TICKS
        else:
            return

        self.label_score.config(text=f"Score : {self.score}")
        if self.plus_aucun_point():
            self.terminer_partie(gagne=True)

    def gerer_collisions_fantomes(self):
        for fantome in self.fantomes:
            if abs(self.joueur["ligne"] - fantome["ligne"]) < 0.6 and abs(self.joueur["colonne"] - fantome["colonne"]) < 0.6:
                if fantome["etat"] == "peur":
                    self.score += POINTS_FANTOME
                    fantome["ligne"], fantome["colonne"] = fantome["origine"]
                    fantome["etat"] = "normal"
                    fantome["compteur_peur"] = 0
                    fantome["direction"] = (0, 0)
                    fantome["direction_voulue"] = (0, 0)
                    self.label_score.config(text=f"Score : {self.score}")
                else:
                    self.perdre_vie()
                    return

    def perdre_vie(self):
        self.vies -= 1
        self.label_vies.config(text="❤" * self.vies if self.vies > 0 else "💔")
        if self.vies <= 0:
            self.terminer_partie(gagne=False)
        else:
            self.joueur["ligne"], self.joueur["colonne"] = float(JOUEUR_SPAWN[0]), float(JOUEUR_SPAWN[1])
            self.joueur["direction"] = (0, 0)
            self.joueur["direction_voulue"] = (0, 0)
            for fantome in self.fantomes:
                fantome["ligne"], fantome["colonne"] = fantome["origine"]
                fantome["direction"] = (0, 0)
                fantome["direction_voulue"] = (0, 0)
                fantome["etat"] = "normal"
                fantome["compteur_peur"] = 0

    # ----- Boucle principale -----

    def boucle_jeu(self):
        self.deplacer_entite(self.joueur, VITESSE_JOUEUR)
        for fantome in self.fantomes:
            self.ia_fantome(fantome)
            vitesse = VITESSE_FANTOME_PEUR if fantome["etat"] == "peur" else VITESSE_FANTOME
            self.deplacer_entite(fantome, vitesse)
            if fantome["etat"] == "peur":
                fantome["compteur_peur"] -= 1
                if fantome["compteur_peur"] <= 0:
                    fantome["etat"] = "normal"

        self.dessiner_pacman()
        for fantome in self.fantomes:
            self.dessiner_fantome(fantome)

        self.gerer_manger()
        if self.etat == "jeu":
            self.gerer_collisions_fantomes()

        if self.etat == "jeu":
            self.id_boucle = self.fenetre.after(DELAI_BOUCLE_MS, self.boucle_jeu)

    # ----- Fin de partie -----

    def terminer_partie(self, gagne):
        self.etat = "fin"

        if self.score > self.donnees.get("meilleur_score", 0):
            self.donnees["meilleur_score"] = self.score

        stats = self.donnees.setdefault("statistiques", {"parties_jouees": 0, "victoires": 0, "total_score": 0})
        stats["parties_jouees"] += 1
        stats["total_score"] += self.score
        if gagne:
            stats["victoires"] += 1

        historique = self.donnees.setdefault("historique", [])
        historique.insert(0, {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "score": self.score,
            "resultat": "Victoire" if gagne else "Défaite",
        })
        del historique[TAILLE_HISTORIQUE:]

        sauvegarder_donnees(self.donnees)
        self.afficher_ecran_fin(gagne)

    def afficher_ecran_fin(self, gagne):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        titre = "🎉 Labyrinthe terminé !" if gagne else "💔 Partie terminée"

        self.canvas.create_rectangle(cx - 150, cy - 105, cx + 150, cy + 115, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.canvas.create_text(cx, cy - 70, text=titre, font=POLICE_INFO, fill=COULEUR_TITRE)
        self.canvas.create_text(cx, cy - 35, text=f"Score : {self.score}", font=POLICE_TITRE, fill=COULEUR_TEXTE)
        self.canvas.create_text(cx, cy, text=f"Meilleur score : {self.donnees.get('meilleur_score', 0)}", font=POLICE_INFO, fill=COULEUR_TITRE)

        self.bouton_rejouer = creer_bouton(self.canvas, "🔄 Rejouer", self.nouvelle_partie)
        self.canvas.create_window(cx, cy + 45, window=self.bouton_rejouer)
        self.bouton_menu_fin = creer_bouton(self.canvas, "🏠 Menu principal", self.retour_menu_jeu)
        self.canvas.create_window(cx, cy + 85, window=self.bouton_menu_fin)

    # ----- Statistiques (écran intégré à la fenêtre) -----

    def afficher_statistiques(self):
        for widget in self.cadre_stats.winfo_children():
            widget.destroy()

        creer_bouton(self.cadre_stats, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(self.cadre_stats, text="📊 Statistiques", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 10))

        meilleur = self.donnees.get("meilleur_score", 0)
        stats = self.donnees.get("statistiques", {"parties_jouees": 0, "victoires": 0, "total_score": 0})
        parties = stats.get("parties_jouees", 0)
        moyenne = stats["total_score"] / parties if parties else 0

        tk.Label(self.cadre_stats, text=f"🏆 Meilleur score : {meilleur}", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Parties jouées : {parties}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Labyrinthes terminés : {stats.get('victoires', 0)}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Score moyen : {moyenne:.1f}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(0, 10))

        tk.Label(self.cadre_stats, text="🕘 Historique récent :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        zone_texte = tk.Text(self.cadre_stats, width=40, height=10, font=POLICE_TEXTE, bg="#fff8fb", fg=COULEUR_TEXTE, relief="flat", bd=6)
        historique = self.donnees.get("historique", [])
        if historique:
            for partie in historique:
                zone_texte.insert(tk.END, f"{partie['date']} - {partie['resultat']} - {partie['score']} pts\n")
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
        if self.id_boucle is not None:
            self.fenetre.after_cancel(self.id_boucle)
        if MUSIQUE_DISPONIBLE:
            pygame.mixer.music.stop()
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    jeu = JeuPacman(fenetre_principale)
    fenetre_principale.mainloop()
