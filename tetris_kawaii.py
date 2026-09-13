"""
Tetris Kawaii en Python avec Tkinter.

Les pièces colorées tombent depuis le haut du plateau : il faut les
empiler pour compléter des lignes entières, qui disparaissent alors et
rapportent des points. Plus vous en faites disparaître d'un coup, plus
le bonus est gros ! En plus des 7 pièces classiques, 21 formes bonus
plus originales (croix, escalier, cœur, pentominos, maison, fleur,
tour, arbre, girafe...) apparaissent de temps en temps pour varier le
jeu — dont plusieurs bien verticales.

Comme le jeu de Mémoire, tout se passe dans une seule fenêtre : un
menu de démarrage permet de lancer une partie, de consulter les
statistiques ou les règles du jeu.

Remarque : comme pour Pac-Man Kawaii, il n'y a pas de bouton
« Reprendre la partie » entre deux lancements du jeu (ce serait un peu
étrange pour un jeu en temps réel). En revanche, une vraie pause est
disponible pendant la partie (touche P ou bouton « Pause »).

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

# ----- Dimensions du plateau -----

TAILLE_CASE = 24
COLONNES_PLATEAU = 10
LIGNES_PLATEAU = 20
LARGEUR_CANVAS = COLONNES_PLATEAU * TAILLE_CASE
HAUTEUR_CANVAS = LIGNES_PLATEAU * TAILLE_CASE

DELAI_CHUTE_INITIAL = 500  # ms entre deux descentes automatiques au niveau 1

TAILLE_HISTORIQUE = 10

# ----- Les 7 pièces classiques et leurs 4 rotations -----
# Chaque rotation est une liste de cases (ligne, colonne) données par
# rapport à un coin d'origine de la pièce.
PIECES_CLASSIQUES = {
    "I": [
        [(1, 0), (1, 1), (1, 2), (1, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 1), (1, 1), (2, 1), (3, 1)],
    ],
    "O": [[(0, 1), (0, 2), (1, 1), (1, 2)]] * 4,
    "T": [
        [(0, 1), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
    ],
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 1), (1, 2), (2, 0), (2, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 2), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    "J": [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (0, 2), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    "L": [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (1, 2), (2, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
}

# ----- Formes bonus « kawaii », plus rares, en plus des 7 classiques -----
# Les 3 premières, puis 10 pentominos classiques (renommés en mode kawaii)
# et 5 formes originales supplémentaires, pour varier encore plus le jeu.
PIECES_BONUS = {
    "CROIX": [[(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]] * 4,
    "ESCALIER": [
        [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2)],
        [(0, 2), (0, 1), (1, 1), (1, 0), (2, 0)],
        [(2, 2), (1, 2), (1, 1), (0, 1), (0, 0)],
        [(2, 0), (2, 1), (1, 1), (1, 2), (0, 2)],
    ],
    "COEUR": [
        [(0, 0), (0, 2), (1, 0), (1, 1), (1, 2), (2, 1)],
        [(0, 2), (2, 2), (0, 1), (1, 1), (2, 1), (1, 0)],
        [(2, 2), (2, 0), (1, 2), (1, 1), (1, 0), (0, 1)],
        [(2, 0), (0, 0), (2, 1), (1, 1), (0, 1), (1, 2)],
    ],
    "PAPILLON": [
        [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)],
        [(1, 2), (2, 2), (0, 1), (1, 1), (1, 0)],
        [(2, 1), (2, 0), (1, 2), (1, 1), (0, 1)],
        [(1, 0), (0, 0), (2, 1), (1, 1), (1, 2)],
    ],
    "BAGUETTE": [
        [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)],
        [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],
        [(0, 4), (0, 3), (0, 2), (0, 1), (0, 0)],
        [(4, 0), (3, 0), (2, 0), (1, 0), (0, 0)],
    ],
    "CANNE": [
        [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1)],
        [(0, 3), (0, 2), (0, 1), (0, 0), (1, 0)],
        [(3, 1), (2, 1), (1, 1), (0, 1), (0, 0)],
        [(1, 0), (1, 1), (1, 2), (1, 3), (0, 3)],
    ],
    "SERPENT": [
        [(0, 1), (1, 1), (2, 0), (2, 1), (3, 0)],
        [(1, 3), (1, 2), (0, 1), (1, 1), (0, 0)],
        [(3, 0), (2, 0), (1, 1), (1, 0), (0, 1)],
        [(0, 0), (0, 1), (1, 2), (0, 2), (1, 3)],
    ],
    "NUAGE": [
        [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0)],
        [(0, 2), (1, 2), (0, 1), (1, 1), (0, 0)],
        [(2, 1), (2, 0), (1, 1), (1, 0), (0, 1)],
        [(1, 0), (0, 0), (1, 1), (0, 1), (1, 2)],
    ],
    "PARAPLUIE": [
        [(0, 0), (0, 1), (0, 2), (1, 1), (2, 1)],
        [(0, 2), (1, 2), (2, 2), (1, 1), (1, 0)],
        [(2, 2), (2, 1), (2, 0), (1, 1), (0, 1)],
        [(2, 0), (1, 0), (0, 0), (1, 1), (1, 2)],
    ],
    "FER_A_CHEVAL": [
        [(0, 0), (0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (2, 1), (0, 0), (1, 0), (2, 0)],
        [(1, 2), (1, 0), (0, 2), (0, 1), (0, 0)],
        [(2, 0), (0, 0), (2, 1), (1, 1), (0, 1)],
    ],
    "EQUERRE": [
        [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)],
        [(0, 2), (0, 1), (0, 0), (1, 0), (2, 0)],
        [(2, 2), (1, 2), (0, 2), (0, 1), (0, 0)],
        [(2, 0), (2, 1), (2, 2), (1, 2), (0, 2)],
    ],
    "BRANCHE": [
        [(0, 1), (1, 0), (1, 1), (2, 1), (3, 1)],
        [(1, 3), (0, 2), (1, 2), (1, 1), (1, 0)],
        [(3, 0), (2, 1), (2, 0), (1, 0), (0, 0)],
        [(0, 0), (1, 1), (0, 1), (0, 2), (0, 3)],
    ],
    "ECLAIR": [
        [(0, 0), (0, 1), (1, 1), (2, 1), (2, 2)],
        [(0, 2), (1, 2), (1, 1), (1, 0), (2, 0)],
        [(2, 2), (2, 1), (1, 1), (0, 1), (0, 0)],
        [(2, 0), (1, 0), (1, 1), (1, 2), (0, 2)],
    ],
    "MAISON": [
        [(0, 1), (1, 0), (1, 1), (1, 2), (2, 0), (2, 2), (3, 0), (3, 2)],
        [(1, 3), (0, 2), (1, 2), (2, 2), (0, 1), (2, 1), (0, 0), (2, 0)],
        [(3, 1), (2, 2), (2, 1), (2, 0), (1, 2), (1, 0), (0, 2), (0, 0)],
        [(1, 0), (2, 1), (1, 1), (0, 1), (2, 2), (0, 2), (2, 3), (0, 3)],
    ],
    "FLEUR": [
        [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1), (3, 1)],
        [(1, 3), (0, 2), (1, 2), (2, 2), (1, 1), (1, 0)],
        [(3, 1), (2, 2), (2, 1), (2, 0), (1, 1), (0, 1)],
        [(1, 0), (2, 1), (1, 1), (0, 1), (1, 2), (1, 3)],
    ],
    "SABLIER": [
        [(0, 0), (0, 1), (0, 2), (1, 1), (2, 1), (3, 0), (3, 1), (3, 2)],
        [(0, 3), (1, 3), (2, 3), (1, 2), (1, 1), (0, 0), (1, 0), (2, 0)],
        [(3, 2), (3, 1), (3, 0), (2, 1), (1, 1), (0, 2), (0, 1), (0, 0)],
        [(2, 0), (1, 0), (0, 0), (1, 1), (1, 2), (2, 3), (1, 3), (0, 3)],
    ],
    "ANCRE": [
        [(0, 1), (1, 1), (2, 1), (3, 0), (3, 1), (3, 2), (4, 0), (4, 2)],
        [(1, 4), (1, 3), (1, 2), (0, 1), (1, 1), (2, 1), (0, 0), (2, 0)],
        [(4, 1), (3, 1), (2, 1), (1, 2), (1, 1), (1, 0), (0, 2), (0, 0)],
        [(1, 0), (1, 1), (1, 2), (2, 3), (1, 3), (0, 3), (2, 4), (0, 4)],
    ],
    "CLE": [
        [(0, 0), (0, 1), (1, 0), (1, 1), (2, 1), (3, 1)],
        [(0, 3), (1, 3), (0, 2), (1, 2), (1, 1), (1, 0)],
        [(3, 1), (3, 0), (2, 1), (2, 0), (1, 0), (0, 0)],
        [(1, 0), (0, 0), (1, 1), (0, 1), (0, 2), (0, 3)],
    ],
    "TOUR": [
        [(0, 0), (0, 1), (0, 2), (1, 1), (2, 1), (3, 1)],
        [(0, 3), (1, 3), (2, 3), (1, 2), (1, 1), (1, 0)],
        [(3, 2), (3, 1), (3, 0), (2, 1), (1, 1), (0, 1)],
        [(2, 0), (1, 0), (0, 0), (1, 1), (1, 2), (1, 3)],
    ],
    "ARBRE": [
        [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1), (3, 1), (4, 1)],
        [(1, 4), (0, 3), (1, 3), (2, 3), (1, 2), (1, 1), (1, 0)],
        [(4, 1), (3, 2), (3, 1), (3, 0), (2, 1), (1, 1), (0, 1)],
        [(1, 0), (2, 1), (1, 1), (0, 1), (1, 2), (1, 3), (1, 4)],
    ],
    "GIRAFE": [
        [(0, 1), (0, 2), (1, 1), (2, 1), (3, 0), (3, 1), (3, 2)],
        [(1, 3), (2, 3), (1, 2), (1, 1), (0, 0), (1, 0), (2, 0)],
        [(3, 1), (3, 0), (2, 1), (1, 1), (0, 2), (0, 1), (0, 0)],
        [(1, 0), (0, 0), (1, 1), (1, 2), (2, 3), (1, 3), (0, 3)],
    ],
}

# Dictionnaire combiné utilisé pour tout le reste du code : peu importe
# qu'une pièce soit classique ou bonus, elle s'y trouve avec ses rotations.
PIECES = {**PIECES_CLASSIQUES, **PIECES_BONUS}

PROBABILITE_PIECE_BONUS = 0.15  # ~15% de chances qu'une pièce bonus apparaisse
BONUS_POINTS_PIECE_SPECIALE = 30  # petit bonus de points quand une pièce bonus se pose


def tirer_type_piece():
    """Choisit le type de la prochaine pièce : le plus souvent une pièce
    classique, parfois une forme bonus plus originale."""
    if random.random() < PROBABILITE_PIECE_BONUS:
        return random.choice(list(PIECES_BONUS.keys()))
    return random.choice(list(PIECES_CLASSIQUES.keys()))

# ----- Palette de couleurs « kawaii » -----
COULEUR_FOND = "#fff0f6"
COULEUR_TITRE = "#d6336c"
COULEUR_TEXTE = "#7c4a9e"
COULEUR_BOUTON = "#f48fb1"
COULEUR_BOUTON_SURVOL = "#f76fa0"

COULEURS_PIECES = {
    "I": "#a0e7e5",
    "O": "#ffe066",
    "T": "#c9a8ff",
    "S": "#b8e8b0",
    "Z": "#ff8fa3",
    "J": "#8ecae6",
    "L": "#ffb98a",
    "CROIX": "#ffd1dc",
    "ESCALIER": "#d4b8ff",
    "COEUR": "#ff6f91",
    "PAPILLON": "#ffb3de",
    "BAGUETTE": "#e0bbff",
    "CANNE": "#ffcc99",
    "SERPENT": "#baffc9",
    "NUAGE": "#bae1ff",
    "PARAPLUIE": "#ffdfba",
    "FER_A_CHEVAL": "#d5aaff",
    "EQUERRE": "#c9ffd8",
    "BRANCHE": "#e8d5b7",
    "ECLAIR": "#fff2a8",
    "MAISON": "#ffcccb",
    "FLEUR": "#ffb7ce",
    "SABLIER": "#b5ead7",
    "ANCRE": "#a8dadc",
    "CLE": "#f1c0e8",
    "TOUR": "#cdb4db",
    "ARBRE": "#a3c9a8",
    "GIRAFE": "#ffe5b4",
}

POLICE_TITRE = ("Comic Sans MS", 22, "bold")
POLICE_SOUS_TITRE = ("Comic Sans MS", 11, "italic")
POLICE_BOUTON = ("Comic Sans MS", 12, "bold")
POLICE_INFO = ("Comic Sans MS", 11, "bold")
POLICE_TEXTE = ("Comic Sans MS", 10)

LARGEUR_BOUTON_MENU = 26

FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tetris_kawaii_sauvegarde.json"
)

# Petite mélodie chiptune en boucle, propre à ce jeu.
FICHIER_MUSIQUE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tetris.wav"
)

REGLES_DU_JEU = (
    "Les pièces tombent depuis le haut du plateau : à vous de les "
    "empiler pour compléter des lignes entières !\n\n"
    "- ← → : déplacer la pièce\n"
    "- ↑ : faire tourner la pièce\n"
    "- ↓ : la faire descendre plus vite\n"
    "- Espace : chute instantanée\n"
    "- P : mettre en pause / reprendre\n\n"
    "Chaque ligne complète disparaît et rapporte des points : plus "
    "vous en faites disparaître d'un coup, plus le bonus est gros ! "
    "Le niveau augmente (et les pièces tombent plus vite) toutes les "
    "10 lignes. La partie se termine quand les pièces atteignent le "
    "haut du plateau.\n\n"
    "De temps en temps, une forme bonus plus originale apparaît (une "
    "croix, un escalier, un cœur, une maison, une fleur, une clé et "
    "bien d'autres !) : elle rapporte quelques points de plus dès "
    "qu'elle se pose."
)


# ----- Sauvegarde / chargement (fichier JSON) -----

def valeurs_par_defaut():
    return {
        "meilleur_score": 0,
        "statistiques": {"parties_jouees": 0, "total_score": 0, "total_lignes": 0},
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


class JeuTetris:
    """Classe principale qui gère la fenêtre, les écrans et la logique du jeu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Tetris Kawaii")
        self.fenetre.configure(bg=COULEUR_FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        self.donnees = charger_donnees()
        self.id_boucle = None
        self.bouton_rejouer = None
        self.bouton_menu_fin = None
        self.en_pause = False
        self.etat = "attente"

        self.cadre_menu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_jeu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_stats = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_regles = tk.Frame(self.fenetre, bg=COULEUR_FOND)

        self.musique_active = MUSIQUE_DISPONIBLE
        demarrer_musique()

        self.construire_ecran_jeu()
        self.construire_ecran_regles()

        self.fenetre.bind_all("<Left>", lambda evenement: self.deplacer_piece(0, -1))
        self.fenetre.bind_all("<Right>", lambda evenement: self.deplacer_piece(0, 1))
        self.fenetre.bind_all("<Down>", lambda evenement: self.chute_rapide())
        self.fenetre.bind_all("<Up>", lambda evenement: self.tourner_piece())
        self.fenetre.bind_all("<space>", lambda evenement: self.chute_totale())
        self.fenetre.bind_all("<p>", lambda evenement: self.basculer_pause())
        self.fenetre.bind_all("<P>", lambda evenement: self.basculer_pause())

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

        tk.Label(self.cadre_menu, text="✨ Tetris Kawaii ✨", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 2))
        tk.Label(self.cadre_menu, text="‧₊˚ Empile et complète des lignes ! ˚₊‧", font=POLICE_SOUS_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(pady=(0, 15))

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
        self.label_score.pack(side=tk.LEFT, padx=6)
        self.label_niveau = tk.Label(cadre_info, text="Niveau : 1", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_niveau.pack(side=tk.LEFT, padx=6)
        self.label_lignes = tk.Label(cadre_info, text="Lignes : 0", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_lignes.pack(side=tk.LEFT, padx=6)
        self.label_meilleur = tk.Label(cadre_info, text="Meilleur score : 0", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_meilleur.pack(side=tk.LEFT, padx=6)

        cadre_zone_jeu = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_zone_jeu.pack(padx=10, pady=5)

        self.canvas = tk.Canvas(cadre_zone_jeu, width=LARGEUR_CANVAS, height=HAUTEUR_CANVAS, bg=COULEUR_FOND, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=(0, 10))

        cadre_suivante = tk.Frame(cadre_zone_jeu, bg=COULEUR_FOND)
        cadre_suivante.pack(side=tk.LEFT, anchor="n", pady=10)
        tk.Label(cadre_suivante, text="Suivante :", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack()
        self.canvas_suivante = tk.Canvas(cadre_suivante, width=TAILLE_CASE * 4, height=TAILLE_CASE * 4, bg="#fff8fb", highlightthickness=0)
        self.canvas_suivante.pack(pady=5)

        cadre_boutons_jeu = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_boutons_jeu.pack(pady=(0, 10))
        creer_bouton(cadre_boutons_jeu, "🔄 Recommencer", self.nouvelle_partie).pack(side=tk.LEFT, padx=5)
        creer_bouton(cadre_boutons_jeu, "⏸ Pause", self.basculer_pause).pack(side=tk.LEFT, padx=5)
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

        self.plateau = [[None] * COLONNES_PLATEAU for _ in range(LIGNES_PLATEAU)]
        self.score = 0
        self.niveau = 1
        self.lignes_completees_total = 0
        self.delai_chute = DELAI_CHUTE_INITIAL
        self.en_pause = False
        self.etat = "jeu"

        self.label_score.config(text="Score : 0")
        self.label_niveau.config(text="Niveau : 1")
        self.label_lignes.config(text="Lignes : 0")
        self.label_meilleur.config(text=f"Meilleur score : {self.donnees.get('meilleur_score', 0)}")

        self.piece_suivante_type = tirer_type_piece()
        self.apparition_nouvelle_piece()
        if self.etat == "jeu":
            self.dessiner_plateau_et_piece()
            self.id_boucle = self.fenetre.after(self.delai_chute, self.tic_gravite)

    def apparition_nouvelle_piece(self):
        self.piece_type = self.piece_suivante_type
        self.piece_suivante_type = tirer_type_piece()
        self.piece_rotation = 0
        self.piece_ligne = -1
        self.piece_colonne = 3
        self.piece_couleur = COULEURS_PIECES[self.piece_type]
        self.dessiner_piece_suivante()
        if not self.peut_placer(self.piece_type, self.piece_rotation, self.piece_ligne, self.piece_colonne):
            self.terminer_partie()

    # ----- Déplacements de la pièce -----

    def peut_placer(self, type_piece, rotation, ligne, colonne):
        for dl, dc in PIECES[type_piece][rotation]:
            l, c = ligne + dl, colonne + dc
            if c < 0 or c >= COLONNES_PLATEAU or l >= LIGNES_PLATEAU:
                return False
            if l >= 0 and self.plateau[l][c] is not None:
                return False
        return True

    def deplacer_piece(self, dl, dc):
        if self.etat != "jeu" or self.en_pause:
            return False
        nouvelle_ligne = self.piece_ligne + dl
        nouvelle_colonne = self.piece_colonne + dc
        if self.peut_placer(self.piece_type, self.piece_rotation, nouvelle_ligne, nouvelle_colonne):
            self.piece_ligne, self.piece_colonne = nouvelle_ligne, nouvelle_colonne
            self.dessiner_plateau_et_piece()
            return True
        return False

    def tourner_piece(self):
        if self.etat != "jeu" or self.en_pause:
            return
        nouvelle_rotation = (self.piece_rotation + 1) % 4
        if self.peut_placer(self.piece_type, nouvelle_rotation, self.piece_ligne, self.piece_colonne):
            self.piece_rotation = nouvelle_rotation
            self.dessiner_plateau_et_piece()

    def chute_rapide(self):
        if self.etat != "jeu" or self.en_pause:
            return
        if self.deplacer_piece(1, 0):
            self.score += 1
            self.label_score.config(text=f"Score : {self.score}")

    def chute_totale(self):
        if self.etat != "jeu" or self.en_pause:
            return
        distance = 0
        while self.peut_placer(self.piece_type, self.piece_rotation, self.piece_ligne + 1, self.piece_colonne):
            self.piece_ligne += 1
            distance += 1
        self.score += distance * 2
        self.label_score.config(text=f"Score : {self.score}")
        self.verrouiller_piece()

    def basculer_pause(self):
        if self.etat != "jeu":
            return
        self.en_pause = not self.en_pause
        if self.en_pause:
            if self.id_boucle is not None:
                self.fenetre.after_cancel(self.id_boucle)
                self.id_boucle = None
            self.afficher_message_pause()
        else:
            self.effacer_message_pause()
            self.id_boucle = self.fenetre.after(self.delai_chute, self.tic_gravite)

    def afficher_message_pause(self):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        self.id_fond_pause = self.canvas.create_rectangle(cx - 90, cy - 30, cx + 90, cy + 30, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.id_texte_pause = self.canvas.create_text(cx, cy, text="⏸ En pause", font=POLICE_INFO, fill=COULEUR_TITRE)

    def effacer_message_pause(self):
        if hasattr(self, "id_fond_pause"):
            self.canvas.delete(self.id_fond_pause)
            self.canvas.delete(self.id_texte_pause)

    # ----- Boucle principale (chute automatique) -----

    def tic_gravite(self):
        if self.etat == "jeu" and not self.en_pause:
            if not self.deplacer_piece(1, 0):
                self.verrouiller_piece()
        if self.etat == "jeu" and not self.en_pause:
            self.id_boucle = self.fenetre.after(self.delai_chute, self.tic_gravite)

    def verrouiller_piece(self):
        for dl, dc in PIECES[self.piece_type][self.piece_rotation]:
            l, c = self.piece_ligne + dl, self.piece_colonne + dc
            if l < 0:
                self.terminer_partie()
                return
            self.plateau[l][c] = self.piece_couleur

        if self.piece_type in PIECES_BONUS:
            self.score += BONUS_POINTS_PIECE_SPECIALE
            self.label_score.config(text=f"Score : {self.score}")

        self.effacer_lignes_completes()
        self.apparition_nouvelle_piece()
        if self.etat == "jeu":
            self.dessiner_plateau_et_piece()

    def effacer_lignes_completes(self):
        lignes_completes = [
            l for l in range(LIGNES_PLATEAU) if all(self.plateau[l][c] is not None for c in range(COLONNES_PLATEAU))
        ]
        if not lignes_completes:
            return

        for l in lignes_completes:
            del self.plateau[l]
            self.plateau.insert(0, [None] * COLONNES_PLATEAU)

        nb = len(lignes_completes)
        points_par_nombre = {1: 100, 2: 300, 3: 500, 4: 800}
        self.score += points_par_nombre.get(nb, 800) * self.niveau
        self.lignes_completees_total += nb
        self.niveau = 1 + self.lignes_completees_total // 10
        self.delai_chute = max(120, DELAI_CHUTE_INITIAL - (self.niveau - 1) * 40)

        self.label_score.config(text=f"Score : {self.score}")
        self.label_niveau.config(text=f"Niveau : {self.niveau}")
        self.label_lignes.config(text=f"Lignes : {self.lignes_completees_total}")

    # ----- Dessin -----

    def dessiner_bloc(self, l, c, couleur):
        x0, y0 = c * TAILLE_CASE, l * TAILLE_CASE
        x1, y1 = x0 + TAILLE_CASE, y0 + TAILLE_CASE
        self.canvas.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill=couleur, outline="#ffffff", width=2)
        self.canvas.create_oval(x0 + 4, y0 + 4, x0 + 9, y0 + 9, fill="#ffffff", outline="")

    def dessiner_plateau_et_piece(self):
        self.canvas.delete("all")
        for l in range(LIGNES_PLATEAU):
            for c in range(COLONNES_PLATEAU):
                x0, y0 = c * TAILLE_CASE, l * TAILLE_CASE
                self.canvas.create_rectangle(x0, y0, x0 + TAILLE_CASE, y0 + TAILLE_CASE, outline="#ffe3ef", fill=COULEUR_FOND)

        for l in range(LIGNES_PLATEAU):
            for c in range(COLONNES_PLATEAU):
                if self.plateau[l][c] is not None:
                    self.dessiner_bloc(l, c, self.plateau[l][c])

        for dl, dc in PIECES[self.piece_type][self.piece_rotation]:
            l, c = self.piece_ligne + dl, self.piece_colonne + dc
            if l >= 0:
                self.dessiner_bloc(l, c, self.piece_couleur)

    def dessiner_piece_suivante(self):
        self.canvas_suivante.delete("all")
        couleur = COULEURS_PIECES[self.piece_suivante_type]
        for dl, dc in PIECES[self.piece_suivante_type][0]:
            x0, y0 = dc * TAILLE_CASE, dl * TAILLE_CASE
            self.canvas_suivante.create_rectangle(x0 + 1, y0 + 1, x0 + TAILLE_CASE - 1, y0 + TAILLE_CASE - 1, fill=couleur, outline="#ffffff", width=2)

    # ----- Fin de partie -----

    def terminer_partie(self):
        self.etat = "fin"

        if self.score > self.donnees.get("meilleur_score", 0):
            self.donnees["meilleur_score"] = self.score

        stats = self.donnees.setdefault("statistiques", {"parties_jouees": 0, "total_score": 0, "total_lignes": 0})
        stats["parties_jouees"] += 1
        stats["total_score"] += self.score
        stats["total_lignes"] += self.lignes_completees_total

        historique = self.donnees.setdefault("historique", [])
        historique.insert(0, {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "score": self.score,
            "niveau": self.niveau,
            "lignes": self.lignes_completees_total,
        })
        del historique[TAILLE_HISTORIQUE:]

        sauvegarder_donnees(self.donnees)
        self.afficher_ecran_fin()

    def afficher_ecran_fin(self):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2

        self.canvas.create_rectangle(cx - 95, cy - 110, cx + 95, cy + 110, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.canvas.create_text(cx, cy - 75, text="💔 Partie terminée", font=POLICE_INFO, fill=COULEUR_TITRE)
        self.canvas.create_text(cx, cy - 40, text=f"Score : {self.score}", font=POLICE_TITRE, fill=COULEUR_TEXTE)
        self.canvas.create_text(cx, cy - 10, text=f"Niveau {self.niveau} · {self.lignes_completees_total} lignes", font=POLICE_TEXTE, fill=COULEUR_TEXTE)
        self.canvas.create_text(cx, cy + 15, text=f"Meilleur score : {self.donnees.get('meilleur_score', 0)}", font=POLICE_INFO, fill=COULEUR_TITRE)

        self.bouton_rejouer = creer_bouton(self.canvas, "🔄 Rejouer", self.nouvelle_partie)
        self.canvas.create_window(cx, cy + 55, window=self.bouton_rejouer)
        self.bouton_menu_fin = creer_bouton(self.canvas, "🏠 Menu principal", self.retour_menu_jeu)
        self.canvas.create_window(cx, cy + 90, window=self.bouton_menu_fin)

    # ----- Statistiques (écran intégré à la fenêtre) -----

    def afficher_statistiques(self):
        for widget in self.cadre_stats.winfo_children():
            widget.destroy()

        creer_bouton(self.cadre_stats, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(self.cadre_stats, text="📊 Statistiques", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 10))

        meilleur = self.donnees.get("meilleur_score", 0)
        stats = self.donnees.get("statistiques", {"parties_jouees": 0, "total_score": 0, "total_lignes": 0})
        parties = stats.get("parties_jouees", 0)
        moyenne = stats["total_score"] / parties if parties else 0

        tk.Label(self.cadre_stats, text=f"🏆 Meilleur score : {meilleur}", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Parties jouées : {parties}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Lignes complétées au total : {stats.get('total_lignes', 0)}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Score moyen : {moyenne:.1f}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(0, 10))

        tk.Label(self.cadre_stats, text="🕘 Historique récent :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        zone_texte = tk.Text(self.cadre_stats, width=42, height=10, font=POLICE_TEXTE, bg="#fff8fb", fg=COULEUR_TEXTE, relief="flat", bd=6)
        historique = self.donnees.get("historique", [])
        if historique:
            for partie in historique:
                zone_texte.insert(tk.END, f"{partie['date']} - {partie['score']} pts - niveau {partie['niveau']} - {partie['lignes']} lignes\n")
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
    jeu = JeuTetris(fenetre_principale)
    fenetre_principale.mainloop()
