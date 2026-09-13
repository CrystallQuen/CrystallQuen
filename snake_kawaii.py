"""
Snake Kawaii en Python avec Tkinter.

Le serpent avance en permanence sur une grille : le joueur ne fait
que choisir sa direction avec les flèches du clavier. Manger une
pomme le fait grandir et rapporte des points, mais la partie se
termine s'il touche un mur ou son propre corps.

Comme le jeu de Mémoire, un menu de démarrage (dans la même fenêtre)
permet de choisir la difficulté avant de lancer une partie, et de
consulter les statistiques ou les règles du jeu.

Remarque : comme pour Pac-Man, Tetris et Fruit Ninja Kawaii, il n'y a
pas de bouton « Reprendre la partie » entre deux lancements du jeu
(jeu en temps réel). Une vraie pause est en revanche disponible en
cours de partie (touche P ou bouton « Pause »), comme dans Tetris.
"""

import json
import os
import random
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

# ----- Dimensions de la grille -----

TAILLE_CASE = 24
COLONNES = 20
LIGNES = 20
LARGEUR_CANVAS = COLONNES * TAILLE_CASE
HAUTEUR_CANVAS = LIGNES * TAILLE_CASE

LONGUEUR_INITIALE = 3
TAILLE_HISTORIQUE = 10

# ----- Niveaux de difficulté : vitesse de départ, vitesse minimale, -----
# ----- et de combien on accélère à chaque pomme mangée. -----
DIFFICULTES = {
    "Facile 🐢": {"delai_initial": 170, "delai_min": 90, "reduction": 2.0},
    "Moyen 🐱": {"delai_initial": 120, "delai_min": 60, "reduction": 2.0},
    "Difficile 🐰": {"delai_initial": 80, "delai_min": 40, "reduction": 1.5},
}

POINTS_POMME = 10
POINTS_POMME_BONUS = 40
PROBABILITE_BONUS = 0.3      # chance qu'une pomme bonus apparaisse après une pomme normale
DUREE_BONUS_TICKS = 45       # nombre de tops d'horloge avant que le bonus ne disparaisse
SEUIL_CLIGNOTEMENT = 15      # à partir de quand le bonus se met à clignoter

# ----- Palette de couleurs « kawaii » -----
COULEUR_FOND = "#fff0f6"
COULEUR_FOND_ALT = "#ffe9f2"
COULEUR_TITRE = "#d6336c"
COULEUR_TEXTE = "#7c4a9e"
COULEUR_BOUTON = "#f48fb1"
COULEUR_BOUTON_SURVOL = "#f76fa0"
COULEUR_TETE = "#4fb477"
COULEUR_CORPS = "#9de8b5"

POLICE_TITRE = ("Comic Sans MS", 22, "bold")
POLICE_SOUS_TITRE = ("Comic Sans MS", 11, "italic")
POLICE_BOUTON = ("Comic Sans MS", 12, "bold")
POLICE_INFO = ("Comic Sans MS", 11, "bold")
POLICE_TEXTE = ("Comic Sans MS", 10)
POLICE_NOURRITURE = ("Arial", 18)

LARGEUR_BOUTON_MENU = 26

FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "snake_kawaii_sauvegarde.json"
)

REGLES_DU_JEU = (
    "Dirigez le serpent avec les flèches du clavier ↑ ↓ ← →.\n\n"
    "- Mangez les pommes 🍎 pour grandir et gagner des points.\n"
    "- Une pomme spéciale ⭐ apparaît parfois : elle rapporte plus de "
    "points mais disparaît vite (elle clignote juste avant de "
    "s'évanouir) !\n"
    "- Le serpent va un peu plus vite à chaque pomme mangée.\n"
    "- La partie se termine si le serpent touche un mur ou son "
    "propre corps.\n"
    "- P : mettre en pause / reprendre.\n\n"
    "Choisissez votre niveau de difficulté dans le menu : plus il "
    "est élevé, plus le serpent démarre vite (et accélère plus fort "
    "à chaque pomme) !"
)


# ----- Sauvegarde / chargement (fichier JSON) -----

def valeurs_par_defaut():
    return {
        "derniere_difficulte": None,
        "records": {},
        "statistiques": {"parties_jouees": 0, "total_score": 0},
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


class JeuSnake:
    """Classe principale qui gère la fenêtre, les écrans et la logique du jeu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Snake Kawaii")
        self.fenetre.configure(bg=COULEUR_FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        self.donnees = charger_donnees()
        self.id_boucle = None
        self.bouton_rejouer = None
        self.bouton_menu_fin = None
        self.en_pause = False
        self.etat = "attente"
        self.id_nourriture = None
        self.id_bonus = None
        self.position_bonus = None

        difficulte_initiale = self.donnees.get("derniere_difficulte") or next(iter(DIFFICULTES))
        self.difficulte_var = tk.StringVar(value=difficulte_initiale)

        self.cadre_menu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_jeu = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_stats = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_regles = tk.Frame(self.fenetre, bg=COULEUR_FOND)

        self.construire_ecran_jeu()
        self.construire_ecran_regles()

        self.fenetre.bind_all("<Up>", lambda evenement: self.touche_direction((-1, 0)))
        self.fenetre.bind_all("<Down>", lambda evenement: self.touche_direction((1, 0)))
        self.fenetre.bind_all("<Left>", lambda evenement: self.touche_direction((0, -1)))
        self.fenetre.bind_all("<Right>", lambda evenement: self.touche_direction((0, 1)))
        self.fenetre.bind_all("<p>", lambda evenement: self.basculer_pause())
        self.fenetre.bind_all("<P>", lambda evenement: self.basculer_pause())

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

        tk.Label(self.cadre_menu, text="✨ Snake Kawaii ✨", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 2))
        tk.Label(self.cadre_menu, text="‧₊˚ Grandis sans te mordre la queue ! ˚₊‧", font=POLICE_SOUS_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(pady=(0, 15))

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
        self.label_score = tk.Label(cadre_info, text="Score : 0", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_score.pack(side=tk.LEFT, padx=6)
        self.label_longueur = tk.Label(cadre_info, text="Longueur : 3", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_longueur.pack(side=tk.LEFT, padx=6)
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
        if self.id_boucle is not None:
            self.fenetre.after_cancel(self.id_boucle)
            self.id_boucle = None
        self.etat = "attente"
        self.afficher_menu()

    # ----- Démarrage d'une partie -----

    def dessiner_fond(self):
        for l in range(LIGNES):
            for c in range(COLONNES):
                x0, y0 = c * TAILLE_CASE, l * TAILLE_CASE
                couleur = COULEUR_FOND if (l + c) % 2 == 0 else COULEUR_FOND_ALT
                self.canvas.create_rectangle(x0, y0, x0 + TAILLE_CASE, y0 + TAILLE_CASE, fill=couleur, outline=couleur, tags="fond")

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
        self.dessiner_fond()

        centre_l, centre_c = LIGNES // 2, COLONNES // 2
        self.serpent = [(centre_l, centre_c), (centre_l, centre_c - 1), (centre_l, centre_c - 2)]
        self.direction = (0, 1)
        self.direction_voulue = (0, 1)

        info_difficulte = DIFFICULTES[self.difficulte_var.get()]
        self.delai = info_difficulte["delai_initial"]

        self.score = 0
        self.etat = "jeu"
        self.en_pause = False
        self.id_nourriture = None
        self.position_bonus = None
        self.id_bonus = None

        self.label_difficulte_jeu.config(text=f"Difficulté : {self.difficulte_var.get()}")
        self.label_score.config(text="Score : 0")
        self.label_longueur.config(text=f"Longueur : {len(self.serpent)}")
        self.mettre_a_jour_record_affiche()

        self.generer_nourriture()
        self.dessiner_serpent()

        self.donnees["derniere_difficulte"] = self.difficulte_var.get()
        sauvegarder_donnees(self.donnees)

        self.tic()

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
            self.tic()

    def afficher_message_pause(self):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        self.id_fond_pause = self.canvas.create_rectangle(cx - 90, cy - 30, cx + 90, cy + 30, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.id_texte_pause = self.canvas.create_text(cx, cy, text="⏸ En pause", font=POLICE_INFO, fill=COULEUR_TITRE)

    def effacer_message_pause(self):
        if hasattr(self, "id_fond_pause"):
            self.canvas.delete(self.id_fond_pause)
            self.canvas.delete(self.id_texte_pause)

    def mettre_a_jour_record_affiche(self):
        record = self.donnees.get("records", {}).get(self.difficulte_var.get())
        if record:
            self.label_record.config(text=f"Record : {record['meilleur_score']} pts (longueur {record['meilleure_longueur']})")
        else:
            self.label_record.config(text="Record : aucun")

    # ----- Nourriture -----

    def cellules_libres(self):
        occupees = set(self.serpent)
        if self.position_bonus is not None:
            occupees.add(self.position_bonus)
        return [(l, c) for l in range(LIGNES) for c in range(COLONNES) if (l, c) not in occupees]

    def generer_nourriture(self):
        libres = self.cellules_libres()
        if not libres:
            self.terminer_partie(gagne=True)
            return
        self.position_nourriture = random.choice(libres)
        l, c = self.position_nourriture
        x, y = c * TAILLE_CASE + TAILLE_CASE / 2, l * TAILLE_CASE + TAILLE_CASE / 2
        if self.id_nourriture is not None:
            self.canvas.delete(self.id_nourriture)
        self.id_nourriture = self.canvas.create_text(x, y, text="🍎", font=POLICE_NOURRITURE, tags="nourriture")

    def generer_bonus(self):
        libres = self.cellules_libres()
        if not libres:
            return
        self.position_bonus = random.choice(libres)
        l, c = self.position_bonus
        x, y = c * TAILLE_CASE + TAILLE_CASE / 2, l * TAILLE_CASE + TAILLE_CASE / 2
        self.id_bonus = self.canvas.create_text(x, y, text="⭐", font=POLICE_NOURRITURE, tags="nourriture")
        self.ticks_bonus_restants = DUREE_BONUS_TICKS

    def gerer_clignotement_bonus(self):
        if self.position_bonus is None or self.ticks_bonus_restants >= SEUIL_CLIGNOTEMENT:
            return
        etat_visible = "normal" if self.ticks_bonus_restants % 4 < 2 else "hidden"
        self.canvas.itemconfigure(self.id_bonus, state=etat_visible)

    # ----- Déplacement -----

    def touche_direction(self, direction):
        if self.etat != "jeu" or self.en_pause:
            return
        oppose = (-self.direction[0], -self.direction[1])
        if direction != oppose:
            self.direction_voulue = direction

    def tic(self):
        if self.etat == "jeu" and not self.en_pause:
            self.deplacer_serpent()
        if self.etat == "jeu" and not self.en_pause:
            self.id_boucle = self.fenetre.after(int(self.delai), self.tic)

    def deplacer_serpent(self):
        oppose = (-self.direction[0], -self.direction[1])
        if self.direction_voulue != oppose:
            self.direction = self.direction_voulue

        dl, dc = self.direction
        tete_l, tete_c = self.serpent[0]
        nouvelle_tete = (tete_l + dl, tete_c + dc)

        if not (0 <= nouvelle_tete[0] < LIGNES and 0 <= nouvelle_tete[1] < COLONNES):
            self.terminer_partie(gagne=False)
            return

        va_manger_normal = nouvelle_tete == self.position_nourriture
        va_manger_bonus = self.position_bonus is not None and nouvelle_tete == self.position_bonus
        va_manger = va_manger_normal or va_manger_bonus

        corps_a_verifier = self.serpent if va_manger else self.serpent[:-1]
        if nouvelle_tete in corps_a_verifier:
            self.terminer_partie(gagne=False)
            return

        self.serpent.insert(0, nouvelle_tete)

        if va_manger_bonus:
            self.score += POINTS_POMME_BONUS
            self.canvas.delete(self.id_bonus)
            self.position_bonus = None
            self.label_score.config(text=f"Score : {self.score}")
            self.label_longueur.config(text=f"Longueur : {len(self.serpent)}")
        elif va_manger_normal:
            self.score += POINTS_POMME
            self.label_score.config(text=f"Score : {self.score}")
            self.label_longueur.config(text=f"Longueur : {len(self.serpent)}")
            self.ajuster_vitesse()
            self.generer_nourriture()
            if self.position_bonus is None and random.random() < PROBABILITE_BONUS:
                self.generer_bonus()
        else:
            self.serpent.pop()
            if self.position_bonus is not None:
                self.ticks_bonus_restants -= 1
                if self.ticks_bonus_restants <= 0:
                    self.canvas.delete(self.id_bonus)
                    self.position_bonus = None
                else:
                    self.gerer_clignotement_bonus()

        self.dessiner_serpent()

    def ajuster_vitesse(self):
        info = DIFFICULTES[self.difficulte_var.get()]
        self.delai = max(info["delai_min"], self.delai - info["reduction"])

    def dessiner_serpent(self):
        self.canvas.delete("serpent")
        for index, (l, c) in enumerate(self.serpent):
            x0, y0 = c * TAILLE_CASE, l * TAILLE_CASE
            x1, y1 = x0 + TAILLE_CASE, y0 + TAILLE_CASE
            couleur = COULEUR_TETE if index == 0 else COULEUR_CORPS
            self.canvas.create_oval(x0 + 2, y0 + 2, x1 - 2, y1 - 2, fill=couleur, outline="#ffffff", width=2, tags="serpent")

        tete_l, tete_c = self.serpent[0]
        cx = tete_c * TAILLE_CASE + TAILLE_CASE / 2
        cy = tete_l * TAILLE_CASE + TAILLE_CASE / 2
        dl, dc = self.direction
        dx, dy = dc * 5, dl * 5
        self.canvas.create_oval(cx - 6 + dx, cy - 4 + dy, cx - 2 + dx, cy + dy, fill=COULEUR_TEXTE, outline="", tags="serpent")
        self.canvas.create_oval(cx + 2 + dx, cy - 4 + dy, cx + 6 + dx, cy + dy, fill=COULEUR_TEXTE, outline="", tags="serpent")

    # ----- Fin de partie -----

    def terminer_partie(self, gagne):
        self.etat = "fin"

        difficulte = self.difficulte_var.get()
        records = self.donnees.setdefault("records", {})
        record = records.get(difficulte)
        self.dernier_resultat_est_record = False
        if record is None or self.score > record["meilleur_score"]:
            records[difficulte] = {"meilleur_score": self.score, "meilleure_longueur": len(self.serpent)}
            self.dernier_resultat_est_record = True

        stats = self.donnees.setdefault("statistiques", {"parties_jouees": 0, "total_score": 0})
        stats["parties_jouees"] += 1
        stats["total_score"] += self.score

        historique = self.donnees.setdefault("historique", [])
        historique.insert(0, {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "difficulte": difficulte,
            "score": self.score,
            "longueur": len(self.serpent),
            "resultat": "Victoire" if gagne else "Défaite",
        })
        del historique[TAILLE_HISTORIQUE:]

        sauvegarder_donnees(self.donnees)
        self.afficher_ecran_fin(gagne)

    def afficher_ecran_fin(self, gagne):
        cx, cy = LARGEUR_CANVAS / 2, HAUTEUR_CANVAS / 2
        titre = "🎉 Grille remplie, bravo !" if gagne else "💔 Partie terminée"

        self.canvas.create_rectangle(cx - 150, cy - 115, cx + 150, cy + 120, fill="#fff0f6", outline=COULEUR_BOUTON, width=3)
        self.canvas.create_text(cx, cy - 80, text=titre, font=POLICE_INFO, fill=COULEUR_TITRE)
        self.canvas.create_text(cx, cy - 45, text=f"Score : {self.score}", font=POLICE_TITRE, fill=COULEUR_TEXTE)
        self.canvas.create_text(cx, cy - 15, text=f"Longueur : {len(self.serpent)}", font=POLICE_TEXTE, fill=COULEUR_TEXTE)
        if self.dernier_resultat_est_record:
            self.canvas.create_text(cx, cy + 10, text="🌟 Nouveau record !", font=POLICE_INFO, fill=COULEUR_TITRE)

        self.bouton_rejouer = creer_bouton(self.canvas, "🔄 Rejouer", self.nouvelle_partie)
        self.canvas.create_window(cx, cy + 60, window=self.bouton_rejouer)
        self.bouton_menu_fin = creer_bouton(self.canvas, "🏠 Menu principal", self.retour_menu_jeu)
        self.canvas.create_window(cx, cy + 95, window=self.bouton_menu_fin)

    # ----- Statistiques (écran intégré à la fenêtre) -----

    def afficher_statistiques(self):
        for widget in self.cadre_stats.winfo_children():
            widget.destroy()

        creer_bouton(self.cadre_stats, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(self.cadre_stats, text="📊 Statistiques", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND).pack(pady=(0, 10))

        stats = self.donnees.get("statistiques", {"parties_jouees": 0, "total_score": 0})
        parties = stats.get("parties_jouees", 0)
        moyenne = stats["total_score"] / parties if parties else 0

        tk.Label(self.cadre_stats, text=f"Parties jouées : {parties}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Score moyen : {moyenne:.1f}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(0, 10))

        tk.Label(self.cadre_stats, text="🏆 Records par difficulté :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        records = self.donnees.get("records", {})
        if records:
            for difficulte, record in records.items():
                tk.Label(
                    self.cadre_stats,
                    text=f"{difficulte} : {record['meilleur_score']} pts (longueur {record['meilleure_longueur']})",
                    font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w",
                ).pack(fill="x", padx=15)
        else:
            tk.Label(self.cadre_stats, text="Aucun record pour l'instant", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", padx=15)

        tk.Label(self.cadre_stats, text="🕘 Historique récent :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(10, 0))
        zone_texte = tk.Text(self.cadre_stats, width=42, height=10, font=POLICE_TEXTE, bg="#fff8fb", fg=COULEUR_TEXTE, relief="flat", bd=6)
        historique = self.donnees.get("historique", [])
        if historique:
            for partie in historique:
                zone_texte.insert(tk.END, f"{partie['date']} - {partie['difficulte']} - {partie['score']} pts - longueur {partie['longueur']} - {partie['resultat']}\n")
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
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    jeu = JeuSnake(fenetre_principale)
    fenetre_principale.mainloop()
