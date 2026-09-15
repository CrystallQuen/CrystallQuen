"""
Mario Kart Kawaii en Python avec Tkinter.

Un jeu de course en pseudo-3D façon Super Mario Kart / Out Run : le
circuit est vu de derrière le kart, le sol défile en perspective et
les virages courbent l'écran. Aucune bibliothèque 3D externe : c'est
la technique classique des vieux jeux de course « pseudo-3D » (parfois
appelée « Mode 7 » sur SNES), où la route est découpée en tronçons
projetés à l'écran plutôt que dessinée pixel par pixel.

Affrontez des karts adverses sur 3 tours de circuit. Flèches Haut/Bas
pour accélérer/freiner, Gauche/Droite pour tourner. Sortir de la route
vous ralentit !

Comme le jeu de Mémoire, un menu de démarrage (dans la même fenêtre)
permet de choisir la difficulté (nombre et vitesse des adversaires),
de lancer une course, et de consulter les statistiques ou les règles.
Comme Tetris et Snake Kawaii, une vraie pause est disponible en course
(touche P) ; pas de « Reprendre la partie » entre deux lancements
(jeu en temps réel).

Remarque technique pour les curieux : pour chaque image, on calcule la
projection en perspective des tronçons de route visibles devant la
caméra (plus loin = plus petit et plus proche du centre de l'écran),
puis on les dessine du plus lointain au plus proche (pour que les
tronçons proches recouvrent correctement les lointains). Les virages
ne déplacent pas réellement la route en 3D : ils décalent simplement,
tronçon après tronçon, la position à l'écran où chacun est projeté —
c'est toute l'astuce qui donne l'illusion d'une route qui tourne.
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
HAUTEUR_CANVAS = 320
HORIZON_Y = HAUTEUR_CANVAS / 2  # la ligne d'horizon est toujours exactement au milieu

# ----- Paramètres de la caméra / projection -----
CHAMP_DE_VISION_DEGRES = 100
CAMERA_PROFONDEUR = 1 / math.tan(math.radians(CHAMP_DE_VISION_DEGRES / 2))
CAMERA_HAUTEUR = 1000

LONGUEUR_SEGMENT = 200
LARGEUR_ROUTE = 2000
DISTANCE_AFFICHAGE = 120  # nombre de tronçons dessinés devant la caméra

# ----- Physique du kart -----
VITESSE_MAX = 34            # unités monde par top d'horloge
ACCELERATION = 1.1
FREINAGE = 2.2
FROTTEMENT = 0.6
VITESSE_VIRAGE = 0.05       # variation du décalage latéral par top, à pleine vitesse
CENTRIFUGE = 0.18           # pousse vers l'extérieur du virage
DECALAGE_MAX = 1.8          # à quel point on peut sortir de la route avant que ça n'ait plus de sens
PENALITE_HORS_PISTE = 0.92  # facteur de ralentissement quand on sort de la route

DELAI_BOUCLE_MS = 45        # ~22 images par seconde

NB_TOURS = 3
TAILLE_HISTORIQUE = 10

# ----- Tracé du circuit : (nombre de tronçons, courbure par tronçon) -----
TRACE_CIRCUIT = [
    (30, 0.0),
    (25, 0.045),
    (30, 0.0),
    (20, -0.06),
    (25, 0.0),
    (20, 0.05),
    (20, -0.04),
    (30, 0.0),
]

# ----- Niveaux de difficulté : nombre et vitesse des adversaires -----
DIFFICULTES = {
    "Facile 🐢": {"nb_ia": 2, "vitesse_min": 0.62, "vitesse_max": 0.78},
    "Moyen 🐱": {"nb_ia": 3, "vitesse_min": 0.75, "vitesse_max": 0.92},
    "Difficile 🐰": {"nb_ia": 4, "vitesse_min": 0.85, "vitesse_max": 1.0},
}

COULEURS_KARTS_IA = ["#ffb3c6", "#a0e7e5", "#ffd59e", "#c9a8ff"]

# ----- Palette de couleurs « kawaii » -----
COULEUR_FOND = "#fff0f6"
COULEUR_TITRE = "#d6336c"
COULEUR_TEXTE = "#7c4a9e"
COULEUR_BOUTON = "#f48fb1"
COULEUR_BOUTON_SURVOL = "#f76fa0"

COULEUR_CIEL = "#bdeaff"
COULEUR_HERBE = "#b8e8b0"
COULEUR_ROUTE_CLAIRE = "#d8bfff"
COULEUR_ROUTE_SOMBRE = "#c9a8ff"
COULEUR_KART_JOUEUR = "#ffe066"

POLICE_TITRE = ("Comic Sans MS", 22, "bold")
POLICE_SOUS_TITRE = ("Comic Sans MS", 11, "italic")
POLICE_BOUTON = ("Comic Sans MS", 12, "bold")
POLICE_INFO = ("Comic Sans MS", 11, "bold")
POLICE_TEXTE = ("Comic Sans MS", 10)

LARGEUR_BOUTON_MENU = 26

FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mario_kart_kawaii_sauvegarde.json"
)

REGLES_DU_JEU = (
    "Prenez le volant façon Mario Kart, vu de derrière le kart !\n\n"
    "- ↑ / ↓ : accélérer / freiner\n"
    "- ← / → : tourner\n"
    "- P : mettre en pause / reprendre\n\n"
    "Restez sur la route : en sortir vous ralentit. Terminez 3 tours "
    "de circuit le plus vite possible, devant les karts adverses !\n\n"
    "Choisissez votre niveau de difficulté dans le menu : plus il est "
    "élevé, plus les adversaires sont nombreux et rapides."
)


# ----- Sauvegarde / chargement (fichier JSON) -----

def valeurs_par_defaut():
    return {
        "derniere_difficulte": None,
        "records": {},
        "statistiques": {"courses_terminees": 0, "victoires": 0},
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


# ----- Construction du circuit -----

def construire_segments():
    """Construit la liste des tronçons du circuit à partir de TRACE_CIRCUIT.
    Chaque tronçon a une courbure (0 = ligne droite) et une couleur en
    damier (bande claire/sombre) pour l'effet visuel de vitesse."""
    segments = []
    for nombre, courbure in TRACE_CIRCUIT:
        for _ in range(nombre):
            segments.append({
                "courbe": courbure,
                "bande_claire": (len(segments) // 3) % 2 == 0,
            })
    return segments


# ----- Projection en perspective -----

def echelle_perspective(z):
    """Facteur d'échelle d'un point situé à une distance `z` (>0) de la
    caméra : plus z est grand, plus l'échelle est petite (effet de
    profondeur)."""
    return CAMERA_PROFONDEUR / max(z, 1)


def projeter_point(x_monde, y_monde, z_relatif, camera_x, camera_y,
                    largeur_ecran=LARGEUR_CANVAS, hauteur_ecran=HAUTEUR_CANVAS,
                    largeur_route=LARGEUR_ROUTE):
    """Projette un point du monde 3D (x, y, à une distance z_relatif
    devant la caméra) sur l'écran 2D. Renvoie (x_ecran, y_ecran,
    demi_largeur_route_ecran, echelle)."""
    echelle = echelle_perspective(z_relatif)
    x_ecran = largeur_ecran / 2 + echelle * (x_monde - camera_x) * (largeur_ecran / 2)
    y_ecran = hauteur_ecran / 2 - echelle * (y_monde - camera_y) * (hauteur_ecran / 2)
    largeur_ecran_route = echelle * largeur_route * (largeur_ecran / 2)
    return x_ecran, y_ecran, largeur_ecran_route, echelle


class JeuMarioKart:
    """Classe principale qui gère la fenêtre, les écrans et le moteur de course."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Mario Kart Kawaii")
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

        self.segments = construire_segments()
        self.longueur_totale = len(self.segments) * LONGUEUR_SEGMENT

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

        tk.Label(self.cadre_menu, text="✨ Mario Kart Kawaii ✨", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 2))
        tk.Label(self.cadre_menu, text="‧₊˚ 3 tours, en piste ! ˚₊‧", font=POLICE_SOUS_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(pady=(0, 15))

        cadre_difficulte = tk.Frame(self.cadre_menu, bg=COULEUR_FOND)
        cadre_difficulte.pack(pady=(0, 10))
        tk.Label(cadre_difficulte, text="Difficulté :", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(side=tk.LEFT, padx=5)
        ttk.Combobox(
            cadre_difficulte, textvariable=self.difficulte_var, values=list(DIFFICULTES.keys()),
            state="readonly", width=14,
        ).pack(side=tk.LEFT, padx=5)

        creer_bouton(self.cadre_menu, "🎀 Nouvelle course", self.demarrer_nouvelle_partie_depuis_menu, LARGEUR_BOUTON_MENU).pack(pady=4)
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
        self.label_tour = tk.Label(cadre_info, text="Tour : 1/3", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_tour.pack(side=tk.LEFT, padx=6)
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

    # ----- Démarrage d'une course -----

    def creer_karts_ia(self):
        info = DIFFICULTES[self.difficulte_var.get()]
        karts = []
        for i in range(info["nb_ia"]):
            karts.append({
                "position": random.uniform(0, LONGUEUR_SEGMENT * 3),
                "tour": 1,
                "decalage": random.uniform(-0.5, 0.5),
                "vitesse": VITESSE_MAX * random.uniform(info["vitesse_min"], info["vitesse_max"]),
                "couleur": COULEURS_KARTS_IA[i % len(COULEURS_KARTS_IA)],
            })
        return karts

    def nouvelle_partie(self):
        self.arreter_boucle()
        self.arreter_chrono()
        if self.bouton_rejouer is not None:
            self.bouton_rejouer.destroy()
            self.bouton_rejouer = None
        if self.bouton_menu_fin is not None:
            self.bouton_menu_fin.destroy()
            self.bouton_menu_fin = None

        self.position = 0.0
        self.vitesse = 0.0
        self.joueur_decalage = 0.0
        self.tour_actuel = 1
        self.karts_ia = self.creer_karts_ia()
        self.touches = {"Up": False, "Down": False, "Left": False, "Right": False}

        self.temps_ecoule = 0
        self.en_pause = False
        self.etat = "jeu"

        self.label_difficulte_jeu.config(text=f"Difficulté : {self.difficulte_var.get()}")
        self.label_tour.config(text=f"Tour : 1/{NB_TOURS}")
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

    # ----- Physique du joueur et des adversaires -----

    def segment_a(self, position):
        return self.segments[int(position / LONGUEUR_SEGMENT) % len(self.segments)]

    def mettre_a_jour_physique(self):
        if self.touches["Up"]:
            self.vitesse = min(VITESSE_MAX, self.vitesse + ACCELERATION)
        elif self.touches["Down"]:
            self.vitesse = max(0.0, self.vitesse - FREINAGE)
        else:
            self.vitesse = max(0.0, self.vitesse - FROTTEMENT)

        pourcentage_vitesse = self.vitesse / VITESSE_MAX
        if self.touches["Left"]:
            self.joueur_decalage -= VITESSE_VIRAGE * pourcentage_vitesse
        if self.touches["Right"]:
            self.joueur_decalage += VITESSE_VIRAGE * pourcentage_vitesse

        segment_actuel = self.segment_a(self.position)
        self.joueur_decalage -= segment_actuel["courbe"] * pourcentage_vitesse * CENTRIFUGE

        if abs(self.joueur_decalage) > 1.0:
            self.vitesse *= PENALITE_HORS_PISTE
        self.joueur_decalage = max(-DECALAGE_MAX, min(DECALAGE_MAX, self.joueur_decalage))

        self.position += self.vitesse
        if self.position >= self.longueur_totale:
            self.position -= self.longueur_totale
            self.tour_actuel += 1
            self.label_tour.config(text=f"Tour : {min(self.tour_actuel, NB_TOURS)}/{NB_TOURS}")
            if self.tour_actuel > NB_TOURS:
                self.terminer_partie()
                return

        for kart in self.karts_ia:
            kart["position"] += kart["vitesse"]
            if kart["position"] >= self.longueur_totale:
                kart["position"] -= self.longueur_totale
                kart["tour"] += 1

    def classement_actuel(self):
        """Renvoie la liste (nom, progression_totale) triée du premier
        au dernier, `progression_totale` combinant le tour et la
        position sur ce tour."""
        participants = [("Vous", self.tour_actuel * self.longueur_totale + self.position)]
        for i, kart in enumerate(self.karts_ia):
            participants.append((f"Kart {i + 1}", kart["tour"] * self.longueur_totale + kart["position"]))
        participants.sort(key=lambda p: -p[1])
        return participants

    # ----- Boucle principale -----

    def boucle_jeu(self):
        if self.etat != "jeu" or self.en_pause:
            return

        self.mettre_a_jour_physique()

        if self.etat == "jeu":
            self.dessiner_scene()
            self.id_boucle = self.fenetre.after(DELAI_BOUCLE_MS, self.boucle_jeu)

    # ----- Rendu (pseudo-3D) -----

    def calculer_segments_visibles(self):
        """Calcule la projection à l'écran des tronçons de route visibles
        devant la caméra. Renvoie (liste des tronçons à dessiner,
        décalage horizontal accumulé pour chacun des DISTANCE_AFFICHAGE
        premiers tronçons — utile pour placer les karts adverses)."""
        n = len(self.segments)
        position_flottante = self.position / LONGUEUR_SEGMENT
        index_base = int(position_flottante) % n
        fraction = position_flottante - int(position_flottante)

        camera_x = self.joueur_decalage * LARGEUR_ROUTE

        x, dx = 0.0, 0.0
        max_y = HAUTEUR_CANVAS + 1
        resultats = []
        decalages_x = []

        for i in range(DISTANCE_AFFICHAGE):
            segment = self.segments[(index_base + i) % n]
            decalages_x.append(x)

            z1 = max((i - fraction) * LONGUEUR_SEGMENT, 1)
            z2 = z1 + LONGUEUR_SEGMENT

            x1, y1, w1, _ = projeter_point(x * LARGEUR_ROUTE, 0, z1, camera_x, CAMERA_HAUTEUR)
            x += dx
            dx += segment["courbe"]
            x2, y2, w2, _ = projeter_point(x * LARGEUR_ROUTE, 0, z2, camera_x, CAMERA_HAUTEUR)

            if y1 < max_y:
                max_y = y1
                resultats.append({
                    "x1": x1, "y1": y1, "w1": w1, "x2": x2, "y2": y2, "w2": w2,
                    "bande_claire": segment["bande_claire"],
                })

        return resultats, decalages_x, camera_x

    def dessiner_scene(self):
        self.canvas.delete("scene")

        self.canvas.create_rectangle(0, 0, LARGEUR_CANVAS, HORIZON_Y, fill=COULEUR_CIEL, outline=COULEUR_CIEL, tags="scene")
        self.canvas.create_rectangle(0, HORIZON_Y, LARGEUR_CANVAS, HAUTEUR_CANVAS, fill=COULEUR_HERBE, outline=COULEUR_HERBE, tags="scene")

        resultats, decalages_x, camera_x = self.calculer_segments_visibles()

        for r in reversed(resultats):
            couleur = COULEUR_ROUTE_CLAIRE if r["bande_claire"] else COULEUR_ROUTE_SOMBRE
            self.canvas.create_polygon(
                r["x1"] - r["w1"], r["y1"], r["x1"] + r["w1"], r["y1"],
                r["x2"] + r["w2"], r["y2"], r["x2"] - r["w2"], r["y2"],
                fill=couleur, outline=couleur, tags="scene",
            )

        self.dessiner_karts_ia(decalages_x, camera_x)
        self.dessiner_kart_joueur()

    def dessiner_karts_ia(self, decalages_x, camera_x):
        karts_visibles = []
        for kart in self.karts_ia:
            z_relatif = (kart["position"] - self.position) % self.longueur_totale
            n_segment = int(z_relatif / LONGUEUR_SEGMENT)
            if 0 <= n_segment < DISTANCE_AFFICHAGE:
                karts_visibles.append((z_relatif, n_segment, kart))

        karts_visibles.sort(key=lambda t: -t[0])  # le plus loin en premier (dessiné en dessous)

        for z_relatif, n_segment, kart in karts_visibles:
            x_route = decalages_x[n_segment]
            x_monde = (x_route + kart["decalage"]) * LARGEUR_ROUTE
            x_ecran, y_ecran, _, echelle = projeter_point(x_monde, 0, max(z_relatif, 1), camera_x, CAMERA_HAUTEUR)
            taille = max(3, echelle * 700)
            self.canvas.create_oval(
                x_ecran - taille, y_ecran - taille * 1.3, x_ecran + taille, y_ecran,
                fill=kart["couleur"], outline="#ffffff", width=2, tags="scene",
            )

    def dessiner_kart_joueur(self):
        cx = LARGEUR_CANVAS / 2 + self.joueur_decalage * 20
        cy = HAUTEUR_CANVAS - 34
        self.canvas.create_oval(cx - 26, cy - 16, cx + 26, cy + 16, fill=COULEUR_KART_JOUEUR, outline="#ffffff", width=3, tags="scene")
        self.canvas.create_oval(cx - 10, cy - 24, cx + 10, cy - 6, fill="#ffffff", outline="", tags="scene")

    # ----- Fin de course -----

    def terminer_partie(self):
        self.etat = "fin"
        self.arreter_boucle()
        self.arreter_chrono()

        classement = self.classement_actuel()
        rang_joueur = next(i for i, (nom, _) in enumerate(classement) if nom == "Vous") + 1
        gagne = rang_joueur == 1

        difficulte = self.difficulte_var.get()
        records = self.donnees.setdefault("records", {})
        record = records.get(difficulte)
        self.dernier_resultat_est_record = False
        if record is None or self.temps_ecoule < record["meilleur_temps"]:
            records[difficulte] = {"meilleur_temps": self.temps_ecoule}
            self.dernier_resultat_est_record = True

        stats = self.donnees.setdefault("statistiques", {"courses_terminees": 0, "victoires": 0})
        stats["courses_terminees"] += 1
        if gagne:
            stats["victoires"] += 1

        historique = self.donnees.setdefault("historique", [])
        historique.insert(0, {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "difficulte": difficulte,
            "temps": self.temps_ecoule,
            "rang": rang_joueur,
            "nb_participants": len(classement),
        })
        del historique[TAILLE_HISTORIQUE:]

        self.rang_final = rang_joueur
        self.nb_participants_final = len(classement)

        sauvegarder_donnees(self.donnees)
        self.afficher_ecran_fin()

    def afficher_ecran_fin(self):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        suffixe = "er" if self.rang_final == 1 else "e"
        titre = "🏆 Victoire !" if self.rang_final == 1 else f"🏁 Arrivée : {self.rang_final}{suffixe} / {self.nb_participants_final}"

        self.canvas.create_rectangle(cx - 145, cy - 95, cx + 145, cy + 100, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.canvas.create_text(cx, cy - 62, text=titre, font=POLICE_INFO, fill=COULEUR_TITRE)
        self.canvas.create_text(cx, cy - 30, text=f"Temps : {self.temps_ecoule} s", font=POLICE_TITRE, fill=COULEUR_TEXTE)
        if self.dernier_resultat_est_record:
            self.canvas.create_text(cx, cy - 2, text="🌟 Nouveau record !", font=POLICE_INFO, fill=COULEUR_TITRE)

        self.bouton_rejouer = creer_bouton(self.canvas, "🔄 Rejouer", self.nouvelle_partie)
        self.canvas.create_window(cx, cy + 45, window=self.bouton_rejouer)
        self.bouton_menu_fin = creer_bouton(self.canvas, "🏠 Menu principal", self.retour_menu_jeu)
        self.canvas.create_window(cx, cy + 80, window=self.bouton_menu_fin)

    # ----- Statistiques (écran intégré à la fenêtre) -----

    def afficher_statistiques(self):
        for widget in self.cadre_stats.winfo_children():
            widget.destroy()

        creer_bouton(self.cadre_stats, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(self.cadre_stats, text="📊 Statistiques", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 10))

        stats = self.donnees.get("statistiques", {"courses_terminees": 0, "victoires": 0})
        courses = stats.get("courses_terminees", 0)
        victoires = stats.get("victoires", 0)

        tk.Label(self.cadre_stats, text=f"Courses terminées : {courses}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Victoires : {victoires}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(0, 10))

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
                zone_texte.insert(tk.END, f"{partie['date']} - {partie['difficulte']} - {partie['temps']} s - {partie['rang']}/{partie['nb_participants']}\n")
        else:
            zone_texte.insert(tk.END, "Aucune course terminée pour l'instant.")
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
    jeu = JeuMarioKart(fenetre_principale)
    fenetre_principale.mainloop()
