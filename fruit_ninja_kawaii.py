"""
Fruit Ninja Kawaii en Python avec Tkinter.

Des fruits (et parfois des bombes !) sont lancés depuis le bas de
l'écran et retombent sous l'effet de la gravité. Faites glisser la
souris dessus (clic maintenu) pour les trancher et gagner des points.
Trancher plusieurs fruits d'un seul geste donne un bonus de combo.
Attention aux bombes : les toucher termine la partie immédiatement !

Comme le jeu de Mémoire, tout se passe dans une seule fenêtre : un
menu de démarrage permet de lancer une partie, de consulter les
statistiques ou les règles du jeu.

Remarque : comme pour Pac-Man et Tetris Kawaii, il n'y a pas de
bouton « Reprendre la partie » entre deux lancements du jeu (jeu en
temps réel, mettre en pause pour reprendre plus tard n'a pas vraiment
de sens ici).

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

# ----- Dimensions et réglages -----

LARGEUR_CANVAS = 480
HAUTEUR_CANVAS = 520

GRAVITE = 0.35
VITESSE_MONTEE_MIN = -12.5
VITESSE_MONTEE_MAX = -9.5
VITESSE_LATERALE_MAX = 1.8

DELAI_BOUCLE_MS = 30  # ~33 images par seconde

RAYON_TRANCHE = 28  # distance (en pixels) en dessous de laquelle un geste tranche un fruit
TAILLE_TRACE_MAX = 20  # nombre de points mémorisés pour dessiner la traînée
DUREE_TRACE_TICKS = 10  # durée de vie (en ticks) d'un point de la traînée

NB_VIES_DEPART = 3
INTERVALLE_SPAWN_INITIAL = 45  # nombre de ticks entre deux apparitions au niveau 1
PROBABILITE_BOMBE_INITIALE = 0.12
FRUITS_PAR_NIVEAU = 20
TAILLE_HISTORIQUE = 10

POINTS_FRUIT = 10
POINTS_COMBO = 15  # bonus par fruit supplémentaire tranché dans le même geste

SYMBOLES_FRUITS = ["🍎", "🍉", "🍓", "🍑", "🍊", "🥝", "🍍", "🍒", "🍋", "🍇"]
SYMBOLE_BOMBE = "💣"
COULEURS_PARTICULES = ["#ffb3c6", "#ffe066", "#baffc9", "#bae1ff", "#ffd6ec"]

# ----- Palette de couleurs « kawaii » -----
COULEUR_FOND = "#fff0f6"
COULEUR_TITRE = "#d6336c"
COULEUR_TEXTE = "#7c4a9e"
COULEUR_BOUTON = "#f48fb1"
COULEUR_BOUTON_SURVOL = "#f76fa0"
COULEUR_TRACE = "#ff6fa5"

POLICE_TITRE = ("Comic Sans MS", 22, "bold")
POLICE_SOUS_TITRE = ("Comic Sans MS", 11, "italic")
POLICE_BOUTON = ("Comic Sans MS", 12, "bold")
POLICE_INFO = ("Comic Sans MS", 11, "bold")
POLICE_TEXTE = ("Comic Sans MS", 10)
POLICE_FRUIT = ("Arial", 38)
POLICE_COMBO = ("Comic Sans MS", 16, "bold")

LARGEUR_BOUTON_MENU = 26

FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fruit_ninja_kawaii_sauvegarde.json"
)

# Petite mélodie chiptune en boucle, propre à ce jeu.
FICHIER_MUSIQUE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fruit_ninja.wav"
)

REGLES_DU_JEU = (
    "Faites glisser la souris (clic maintenu) sur les fruits qui "
    "s'envolent pour les trancher !\n\n"
    "- Chaque fruit tranché rapporte des points.\n"
    "- Trancher plusieurs fruits dans un même geste donne un bonus "
    "de combo !\n"
    "- Ne touchez surtout pas les bombes 💣 : ça termine la partie "
    "immédiatement !\n"
    "- Si un fruit tombe sans être tranché, vous perdez une vie. "
    "Vous avez 3 vies.\n\n"
    "Le niveau augmente avec le nombre de fruits tranchés : les "
    "fruits (et les bombes) apparaissent alors plus souvent."
)


# ----- Sauvegarde / chargement (fichier JSON) -----

def valeurs_par_defaut():
    return {
        "meilleur_score": 0,
        "statistiques": {"parties_jouees": 0, "total_score": 0, "total_fruits_tranches": 0},
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


def distance_segment_point(x0, y0, x1, y1, px, py):
    """Distance entre le point (px, py) et le segment [(x0,y0)-(x1,y1)]."""
    dx, dy = x1 - x0, y1 - y0
    longueur_carre = dx * dx + dy * dy
    if longueur_carre == 0:
        return ((px - x0) ** 2 + (py - y0) ** 2) ** 0.5
    t = max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / longueur_carre))
    proj_x, proj_y = x0 + t * dx, y0 + t * dy
    return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5


class JeuFruitNinja:
    """Classe principale qui gère la fenêtre, les écrans et la logique du jeu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Fruit Ninja Kawaii")
        self.fenetre.configure(bg=COULEUR_FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        self.donnees = charger_donnees()
        self.id_boucle = None
        self.bouton_rejouer = None
        self.bouton_menu_fin = None
        self.etat = "attente"
        self.derniere_pos_souris = None
        self.trace_points = []
        self.ids_trace = []

        self.cadre_menu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_jeu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_stats = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_regles = tk.Frame(self.fenetre, bg=COULEUR_FOND)

        self.musique_active = MUSIQUE_DISPONIBLE
        demarrer_musique()

        self.construire_ecran_jeu()
        self.construire_ecran_regles()

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

        tk.Label(self.cadre_menu, text="✨ Fruit Ninja Kawaii ✨", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 2))
        tk.Label(self.cadre_menu, text="‧₊˚ Tranchez les fruits, évitez les bombes ! ˚₊‧", font=POLICE_SOUS_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(pady=(0, 15))

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
        self.label_score.pack(side=tk.LEFT, padx=8)
        self.label_vies = tk.Label(cadre_info, text="❤❤❤", font=POLICE_INFO, fg=COULEUR_TITRE, bg=COULEUR_FOND)
        self.label_vies.pack(side=tk.LEFT, padx=8)
        self.label_niveau = tk.Label(cadre_info, text="Niveau : 1", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_niveau.pack(side=tk.LEFT, padx=8)
        self.label_meilleur = tk.Label(cadre_info, text="Meilleur score : 0", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_meilleur.pack(side=tk.LEFT, padx=8)

        self.canvas = tk.Canvas(self.cadre_jeu, width=LARGEUR_CANVAS, height=HAUTEUR_CANVAS, bg=COULEUR_FOND, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(padx=10, pady=5)
        self.canvas.bind("<ButtonPress-1>", self.debut_glissade)
        self.canvas.bind("<B1-Motion>", self.pendant_glissade)
        self.canvas.bind("<ButtonRelease-1>", self.fin_glissade)

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
        self.objets_actifs = []
        self.trace_points = []
        self.ids_trace = []
        self.derniere_pos_souris = None
        self.fruits_tranches_glissade = 0

        self.score = 0
        self.vies = NB_VIES_DEPART
        self.fruits_tranches = 0
        self.niveau = 1
        self.intervalle_spawn = INTERVALLE_SPAWN_INITIAL
        self.probabilite_bombe = PROBABILITE_BOMBE_INITIALE
        self.compteur_spawn = 0

        self.label_score.config(text="Score : 0")
        self.label_vies.config(text="❤" * self.vies)
        self.label_niveau.config(text="Niveau : 1")
        self.label_meilleur.config(text=f"Meilleur score : {self.donnees.get('meilleur_score', 0)}")

        self.etat = "jeu"
        self.apparition_objet()
        self.boucle_jeu()

    # ----- Apparition des fruits / bombes -----

    def apparition_objet(self):
        nombre = 2 if random.random() < 0.25 else 1
        for _ in range(nombre):
            est_bombe = random.random() < self.probabilite_bombe
            symbole = SYMBOLE_BOMBE if est_bombe else random.choice(SYMBOLES_FRUITS)
            x = random.uniform(40, LARGEUR_CANVAS - 40)
            vx = random.uniform(-VITESSE_LATERALE_MAX, VITESSE_LATERALE_MAX)
            vy = random.uniform(VITESSE_MONTEE_MAX, VITESSE_MONTEE_MIN)
            y = HAUTEUR_CANVAS + 20
            identifiant = self.canvas.create_text(x, y, text=symbole, font=POLICE_FRUIT)
            self.objets_actifs.append({
                "type": "bombe" if est_bombe else "fruit",
                "x": x, "y": y, "vx": vx, "vy": vy, "id": identifiant,
            })

    # ----- Glisser-trancher à la souris -----

    def debut_glissade(self, evenement):
        if self.etat != "jeu":
            return
        self.derniere_pos_souris = (evenement.x, evenement.y)
        self.fruits_tranches_glissade = 0

    def pendant_glissade(self, evenement):
        if self.etat != "jeu":
            return
        x, y = evenement.x, evenement.y
        self.trace_points.append([x, y, 0])
        if len(self.trace_points) > TAILLE_TRACE_MAX:
            self.trace_points.pop(0)

        if self.derniere_pos_souris is not None:
            x0, y0 = self.derniere_pos_souris
            self.fruits_tranches_glissade += self.verifier_tranchage(x0, y0, x, y)
        self.derniere_pos_souris = (x, y)

    def fin_glissade(self, evenement):
        self.derniere_pos_souris = None
        self.fruits_tranches_glissade = 0

    def verifier_tranchage(self, x0, y0, x1, y1):
        tranches = 0
        for objet in list(self.objets_actifs):
            if distance_segment_point(x0, y0, x1, y1, objet["x"], objet["y"]) >= RAYON_TRANCHE:
                continue
            if objet["type"] == "bombe":
                self.canvas.delete(objet["id"])
                self.objets_actifs.remove(objet)
                self.terminer_partie("bombe")
                return tranches
            self.canvas.delete(objet["id"])
            self.objets_actifs.remove(objet)
            self.fruits_tranches += 1
            self.creer_particules(objet["x"], objet["y"])
            tranches += 1

        if tranches > 0:
            bonus = POINTS_FRUIT * tranches + (POINTS_COMBO * (tranches - 1) if tranches > 1 else 0)
            self.score += bonus
            self.label_score.config(text=f"Score : {self.score}")
            if tranches > 1:
                self.afficher_message_combo(tranches)
            self.mettre_a_jour_niveau()
        return tranches

    def mettre_a_jour_niveau(self):
        nouveau_niveau = 1 + self.fruits_tranches // FRUITS_PAR_NIVEAU
        if nouveau_niveau == self.niveau:
            return
        self.niveau = nouveau_niveau
        self.intervalle_spawn = max(18, INTERVALLE_SPAWN_INITIAL - (self.niveau - 1) * 3)
        self.probabilite_bombe = min(0.30, PROBABILITE_BOMBE_INITIALE + (self.niveau - 1) * 0.02)
        self.label_niveau.config(text=f"Niveau : {self.niveau}")

    # ----- Effets visuels -----

    def supprimer_en_securite(self, identifiant):
        try:
            self.canvas.delete(identifiant)
        except tk.TclError:
            pass

    def creer_particules(self, x, y):
        couleur = random.choice(COULEURS_PARTICULES)
        for _ in range(6):
            dx = random.uniform(-18, 18)
            dy = random.uniform(-18, 18)
            taille = random.uniform(3, 6)
            particule = self.canvas.create_oval(x + dx - taille, y + dy - taille, x + dx + taille, y + dy + taille, fill=couleur, outline="")
            self.fenetre.after(400, lambda p=particule: self.supprimer_en_securite(p))

    def afficher_message_combo(self, nombre):
        texte = self.canvas.create_text(LARGEUR_CANVAS / 2, 60, text=f"✨ Combo x{nombre} ! ✨", font=POLICE_COMBO, fill=COULEUR_TITRE)
        self.fenetre.after(700, lambda t=texte: self.supprimer_en_securite(t))

    def dessiner_trace(self):
        for identifiant in self.ids_trace:
            self.canvas.delete(identifiant)
        self.ids_trace = []
        points = self.trace_points
        for i in range(1, len(points)):
            x0, y0, _ = points[i - 1]
            x1, y1, age1 = points[i]
            largeur = max(1, 6 - age1 // 2)
            self.ids_trace.append(self.canvas.create_line(x0, y0, x1, y1, fill=COULEUR_TRACE, width=largeur, capstyle=tk.ROUND))

    # ----- Boucle principale -----

    def boucle_jeu(self):
        for objet in list(self.objets_actifs):
            if self.etat != "jeu":
                break
            objet["vy"] += GRAVITE
            objet["x"] += objet["vx"]
            objet["y"] += objet["vy"]
            self.canvas.coords(objet["id"], objet["x"], objet["y"])
            if objet["y"] > HAUTEUR_CANVAS + 40:
                self.canvas.delete(objet["id"])
                self.objets_actifs.remove(objet)
                if objet["type"] == "fruit":
                    self.perdre_vie()

        if self.etat == "jeu":
            for point in self.trace_points:
                point[2] += 1
            self.trace_points = [p for p in self.trace_points if p[2] <= DUREE_TRACE_TICKS]
            self.dessiner_trace()

            self.compteur_spawn += 1
            if self.compteur_spawn >= self.intervalle_spawn:
                self.compteur_spawn = 0
                self.apparition_objet()

            self.id_boucle = self.fenetre.after(DELAI_BOUCLE_MS, self.boucle_jeu)

    def perdre_vie(self):
        self.vies -= 1
        self.label_vies.config(text="❤" * self.vies if self.vies > 0 else "💔")
        if self.vies <= 0:
            self.terminer_partie("vies")

    # ----- Fin de partie -----

    def terminer_partie(self, raison):
        self.etat = "fin"

        if self.score > self.donnees.get("meilleur_score", 0):
            self.donnees["meilleur_score"] = self.score

        stats = self.donnees.setdefault("statistiques", {"parties_jouees": 0, "total_score": 0, "total_fruits_tranches": 0})
        stats["parties_jouees"] += 1
        stats["total_score"] += self.score
        stats["total_fruits_tranches"] += self.fruits_tranches

        historique = self.donnees.setdefault("historique", [])
        historique.insert(0, {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "score": self.score,
            "fruits": self.fruits_tranches,
            "raison": "Bombe" if raison == "bombe" else "Fruits ratés",
        })
        del historique[TAILLE_HISTORIQUE:]

        sauvegarder_donnees(self.donnees)
        self.afficher_ecran_fin(raison)

    def afficher_ecran_fin(self, raison):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        titre = "💣 Boum ! Une bombe a explosé !" if raison == "bombe" else "💔 Trop de fruits ratés !"

        self.canvas.create_rectangle(cx - 150, cy - 110, cx + 150, cy + 115, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.canvas.create_text(cx, cy - 75, text=titre, font=POLICE_INFO, fill=COULEUR_TITRE)
        self.canvas.create_text(cx, cy - 40, text=f"Score : {self.score}", font=POLICE_TITRE, fill=COULEUR_TEXTE)
        self.canvas.create_text(cx, cy - 10, text=f"{self.fruits_tranches} fruits tranchés", font=POLICE_TEXTE, fill=COULEUR_TEXTE)
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
        stats = self.donnees.get("statistiques", {"parties_jouees": 0, "total_score": 0, "total_fruits_tranches": 0})
        parties = stats.get("parties_jouees", 0)
        moyenne = stats["total_score"] / parties if parties else 0

        tk.Label(self.cadre_stats, text=f"🏆 Meilleur score : {meilleur}", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Parties jouées : {parties}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Fruits tranchés au total : {stats.get('total_fruits_tranches', 0)}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Score moyen : {moyenne:.1f}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(0, 10))

        tk.Label(self.cadre_stats, text="🕘 Historique récent :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        zone_texte = tk.Text(self.cadre_stats, width=42, height=10, font=POLICE_TEXTE, bg="#fff8fb", fg=COULEUR_TEXTE, relief="flat", bd=6)
        historique = self.donnees.get("historique", [])
        if historique:
            for partie in historique:
                zone_texte.insert(tk.END, f"{partie['date']} - {partie['score']} pts - {partie['fruits']} fruits - {partie['raison']}\n")
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
    jeu = JeuFruitNinja(fenetre_principale)
    fenetre_principale.mainloop()
