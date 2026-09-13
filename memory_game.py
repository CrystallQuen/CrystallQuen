"""
Jeu de Mémoire (Memory) en Python avec Tkinter.

Règle du jeu : une grille de cartes est affichée face cachée. Le joueur
clique sur deux cartes ; si elles correspondent, elles restent
visibles, sinon elles se recachent après une courte pause. Le but est
de retrouver toutes les paires en un minimum de coups et de temps.

Fonctionnalités :
- Menu de démarrage (nouvelle partie, reprise, statistiques, règles...).
- Plusieurs niveaux de difficulté (taille de grille différente).
- Chronomètre et compteur de coups.
- Sauvegarde automatique des meilleurs scores et de l'historique des
  parties dans un fichier JSON à côté de ce script.
- Reprise d'une partie interrompue (retour au menu ou fermeture de la
  fenêtre en cours de jeu).
- Tout se passe dans une seule et même fenêtre : le menu, la partie,
  les statistiques et les règles sont de simples écrans que l'on
  affiche ou masque à l'intérieur de cette fenêtre.
"""

import json
import os
import random
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

# ----- Constantes de configuration -----

# Les différents niveaux de difficulté disponibles : chaque niveau
# définit le nombre de lignes et de colonnes de la grille de cartes.
DIFFICULTES = {
    "Facile (4x4)": {"lignes": 4, "colonnes": 4},
    "Moyen (4x6)": {"lignes": 4, "colonnes": 6},
    "Difficile (6x6)": {"lignes": 6, "colonnes": 6},
}

# 18 symboles différents : suffisant pour la difficulté la plus dure
# (6x6 = 36 cartes = 18 paires).
SYMBOLES_DISPONIBLES = [
    "🍎", "🍌", "🍇", "🍓", "🍒", "🍍", "🥝", "🍑", "🍋",
    "🍉", "🥥", "🍈", "🐶", "🐱", "🐵", "🦊", "🐼", "🐸",
]

SYMBOLE_DOS_CARTE = "💗"  # petit cœur affiché au dos des cartes cachées

# ----- Palette de couleurs « kawaii » (tons pastel) -----
COULEUR_FOND = "#fff0f6"          # rose très clair, fond de toute la fenêtre
COULEUR_CACHEE = "#c9a8ff"        # lavande, carte face cachée
COULEUR_DECOUVERTE = "#fff6da"    # crème, carte retournée (pas encore validée)
COULEUR_TROUVEE = "#baf2d0"       # menthe pastel, paire trouvée
COULEUR_BOUTON = "#f48fb1"        # rose bonbon, boutons
COULEUR_BOUTON_SURVOL = "#f76fa0"  # rose un peu plus soutenu au clic
COULEUR_TITRE = "#d6336c"         # rose vif, titres
COULEUR_TEXTE = "#7c4a9e"         # violet doux, texte normal

# ----- Polices « kawaii » (arrondies) -----
POLICE_TITRE = ("Comic Sans MS", 22, "bold")
POLICE_SOUS_TITRE = ("Comic Sans MS", 11, "italic")
POLICE_BOUTON = ("Comic Sans MS", 12, "bold")
POLICE_INFO = ("Comic Sans MS", 11, "bold")
POLICE_CARTE = ("Comic Sans MS", 16, "bold")
POLICE_TEXTE = ("Comic Sans MS", 10)

DELAI_RETOURNEMENT_MS = 1000  # délai (ms) avant de recacher deux cartes

LARGEUR_BOUTON_MENU = 26  # largeur commune des boutons du menu principal

# Fichier de sauvegarde, toujours créé à côté de ce script.
FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "memory_sauvegarde.json"
)

# Nombre maximal de parties conservées dans l'historique.
TAILLE_HISTORIQUE = 20

REGLES_DU_JEU = (
    "Le but du jeu est de retrouver toutes les paires de cartes identiques.\n\n"
    "- Cliquez sur une carte pour la retourner et découvrir son symbole.\n"
    "- Vous pouvez retourner deux cartes maximum en même temps.\n"
    "- Si les deux cartes correspondent, elles restent découvertes.\n"
    "- Sinon, elles se recachent après environ 1 seconde.\n"
    "- Chaque paire de cartes retournées compte pour un coup.\n"
    "- La partie est terminée quand toutes les paires ont été trouvées.\n\n"
    "Essayez de terminer en un minimum de coups et de temps pour battre "
    "votre record !"
)


# ----- Fonctions de sauvegarde / chargement (fichier JSON) -----

def valeurs_par_defaut():
    """Retourne la structure de données utilisée quand il n'y a pas
    encore de fichier de sauvegarde (ou qu'il est illisible)."""
    return {
        "derniere_difficulte": None,
        "partie_en_cours": None,
        "records": {},
        "historique": [],
        "statistiques": {"parties_terminees": 0, "total_coups": 0, "total_temps": 0},
    }


def charger_donnees():
    """Charge les données de sauvegarde depuis le disque, ou renvoie
    des valeurs par défaut si le fichier n'existe pas / est corrompu."""
    donnees = valeurs_par_defaut()
    if not os.path.exists(FICHIER_SAUVEGARDE):
        return donnees
    try:
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as fichier:
            donnees.update(json.load(fichier))
    except (json.JSONDecodeError, OSError):
        # Fichier illisible ou corrompu : on repart sur des valeurs vides
        # plutôt que de planter le jeu.
        return valeurs_par_defaut()
    return donnees


def sauvegarder_donnees(donnees):
    """Écrit les données de sauvegarde sur le disque."""
    try:
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as fichier:
            json.dump(donnees, fichier, ensure_ascii=False, indent=2)
    except OSError as erreur:
        messagebox.showwarning(
            "Sauvegarde impossible",
            f"Impossible d'enregistrer la sauvegarde :\n{erreur}",
        )


def creer_bouton(parent, texte, commande, largeur=None):
    """Crée un bouton avec le style « kawaii » commun à tout le jeu."""
    return tk.Button(
        parent,
        text=texte,
        font=POLICE_BOUTON,
        command=commande,
        bg=COULEUR_BOUTON,
        fg="#ffffff",
        activebackground=COULEUR_BOUTON_SURVOL,
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        padx=14,
        pady=6,
        width=largeur,
        cursor="hand2",
    )


class JeuMemoire:
    """Classe principale qui gère la fenêtre, les écrans et la logique du jeu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Jeu de Mémoire")
        self.fenetre.configure(bg=COULEUR_FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        # Petite touche de style pour le menu déroulant de difficulté.
        style = ttk.Style(self.fenetre)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TCombobox", fieldbackground=COULEUR_DECOUVERTE, background=COULEUR_BOUTON,
        )

        self.donnees = charger_donnees()

        # État de la partie en cours
        self.id_chrono = None       # identifiant after() du chronomètre, pour pouvoir l'annuler
        self.nombre_coups = 0
        self.temps_ecoule = 0
        self.cartes_retournees = []
        self.clic_bloque = False
        self.partie_terminee = True  # aucune partie n'a encore démarré
        self.boutons = []
        self.dernier_resultat_est_record = False
        self.ecran_precedent = "menu"  # pour savoir où revenir depuis les statistiques

        difficulte_initiale = self.donnees.get("derniere_difficulte") or next(iter(DIFFICULTES))
        self.difficulte_var = tk.StringVar(value=difficulte_initiale)

        # Tous les écrans du jeu vivent dans la même fenêtre : on affiche
        # l'un d'eux à la fois avec pack()/pack_forget().
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
        """Construit (ou reconstruit) et affiche le menu de démarrage."""
        for widget in self.cadre_menu.winfo_children():
            widget.destroy()
        self.masquer_tous_les_ecrans()
        self.cadre_menu.pack(padx=30, pady=20)

        tk.Label(
            self.cadre_menu, text="✨ Jeu de Mémoire ✨", font=POLICE_TITRE,
            fg=COULEUR_TITRE, bg=COULEUR_FOND,
        ).pack(pady=(0, 2))
        tk.Label(
            self.cadre_menu, text="‧₊˚ Trouve toutes les paires ! ˚₊‧", font=POLICE_SOUS_TITRE,
            fg=COULEUR_TEXTE, bg=COULEUR_FOND,
        ).pack(pady=(0, 15))

        cadre_difficulte = tk.Frame(self.cadre_menu, bg=COULEUR_FOND)
        cadre_difficulte.pack(pady=(0, 10))
        tk.Label(cadre_difficulte, text="Difficulté :", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND).pack(side=tk.LEFT, padx=5)
        ttk.Combobox(
            cadre_difficulte,
            textvariable=self.difficulte_var,
            values=list(DIFFICULTES.keys()),
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT, padx=5)

        creer_bouton(self.cadre_menu, "🎀 Nouvelle partie", self.demarrer_nouvelle_partie_depuis_menu, LARGEUR_BOUTON_MENU).pack(pady=4)

        bouton_reprendre = creer_bouton(self.cadre_menu, "🍡 Reprendre la partie", self.reprendre_partie_depuis_menu, LARGEUR_BOUTON_MENU)
        bouton_reprendre.pack(pady=4)
        if not self.donnees.get("partie_en_cours"):
            bouton_reprendre.config(state="disabled", bg="#f6c9db")

        creer_bouton(self.cadre_menu, "📊 Statistiques", lambda: self.afficher_statistiques("menu"), LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "📖 Règles du jeu", self.afficher_regles, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "🧹 Réinitialiser les statistiques", self.reinitialiser_statistiques, LARGEUR_BOUTON_MENU).pack(pady=4)
        creer_bouton(self.cadre_menu, "🚪 Quitter", self.fenetre.destroy, LARGEUR_BOUTON_MENU).pack(pady=(4, 0))

    def demarrer_nouvelle_partie_depuis_menu(self):
        if self.donnees.get("partie_en_cours") and not messagebox.askyesno(
            "Nouvelle partie",
            "Une partie sauvegardée existe. La remplacer par une nouvelle partie ?",
        ):
            return
        self.nouvelle_partie()
        self.afficher_ecran_jeu()

    def reprendre_partie_depuis_menu(self):
        partie_sauvee = self.donnees.get("partie_en_cours")
        if not partie_sauvee:
            return
        self.reprendre_partie(partie_sauvee)
        self.afficher_ecran_jeu()

    def reinitialiser_statistiques(self):
        if not messagebox.askyesno(
            "Réinitialiser les statistiques",
            "Effacer tous les records, l'historique et les statistiques ? "
            "Cette action est irréversible.",
        ):
            return
        self.donnees["records"] = {}
        self.donnees["historique"] = []
        self.donnees["statistiques"] = {"parties_terminees": 0, "total_coups": 0, "total_temps": 0}
        sauvegarder_donnees(self.donnees)
        messagebox.showinfo("Réinitialisation", "Les statistiques ont été réinitialisées.")

    # ----- Écran de jeu -----

    def construire_ecran_jeu(self):
        """Crée une seule fois les widgets fixes de l'écran de jeu (les
        infos en haut et le cadre qui accueillera la grille de cartes)."""
        cadre_info = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_info.pack(pady=10)

        self.label_difficulte_jeu = tk.Label(cadre_info, text="", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_difficulte_jeu.pack(side=tk.LEFT, padx=8)

        self.label_coups = tk.Label(cadre_info, text="Coups : 0", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_coups.pack(side=tk.LEFT, padx=8)

        self.label_chrono = tk.Label(cadre_info, text="Temps : 0 s", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_chrono.pack(side=tk.LEFT, padx=8)

        self.label_record = tk.Label(cadre_info, text="Record : aucun", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND)
        self.label_record.pack(side=tk.LEFT, padx=8)

        self.cadre_grille = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        self.cadre_grille.pack(padx=10, pady=10)

        cadre_boutons_jeu = tk.Frame(self.cadre_jeu, bg=COULEUR_FOND)
        cadre_boutons_jeu.pack(pady=(0, 10))
        creer_bouton(cadre_boutons_jeu, "🔄 Recommencer", self.demander_nouvelle_partie).pack(side=tk.LEFT, padx=5)
        creer_bouton(cadre_boutons_jeu, "📊 Statistiques", lambda: self.afficher_statistiques("jeu")).pack(side=tk.LEFT, padx=5)
        creer_bouton(cadre_boutons_jeu, "🏠 Menu principal", self.retour_menu).pack(side=tk.LEFT, padx=5)

    def afficher_ecran_jeu(self):
        self.masquer_tous_les_ecrans()
        self.cadre_jeu.pack(padx=10, pady=10)

    def retour_menu(self):
        """Sauvegarde la partie en cours (si besoin) et revient au menu."""
        self.arreter_chrono()
        self.sauvegarder_partie_en_cours()
        self.afficher_menu()

    # ----- Gestion de la difficulté -----

    def dimensions_actuelles(self):
        info = DIFFICULTES[self.difficulte_var.get()]
        return info["lignes"], info["colonnes"]

    def mettre_a_jour_record_affiche(self):
        record = self.donnees.get("records", {}).get(self.difficulte_var.get())
        if record:
            self.label_record.config(
                text=f"Record : {record['meilleurs_coups']} coups en {record['meilleur_temps']} s"
            )
        else:
            self.label_record.config(text="Record : aucun")

    # ----- Démarrage / reprise de partie -----

    def demander_nouvelle_partie(self):
        """Appelée par le bouton « Recommencer » : demande confirmation
        si une partie non terminée risque d'être perdue."""
        if not self.partie_terminee and self.nombre_coups > 0:
            if not messagebox.askyesno(
                "Recommencer", "Une partie est en cours. L'abandonner et en commencer une nouvelle ?"
            ):
                return
        self.nouvelle_partie()

    def nouvelle_partie(self):
        """Prépare une nouvelle grille mélangée et réinitialise l'état du jeu."""
        self.arreter_chrono()

        lignes, colonnes = self.dimensions_actuelles()
        nb_paires = (lignes * colonnes) // 2
        self.symboles_grille = SYMBOLES_DISPONIBLES[:nb_paires] * 2
        random.shuffle(self.symboles_grille)
        self.cartes_trouvees = [False] * len(self.symboles_grille)

        self.cartes_retournees = []
        self.clic_bloque = False
        self.nombre_coups = 0
        self.temps_ecoule = 0
        self.partie_terminee = False

        self.label_difficulte_jeu.config(text=f"Difficulté : {self.difficulte_var.get()}")
        self.label_coups.config(text="Coups : 0")
        self.label_chrono.config(text="Temps : 0 s")
        self.mettre_a_jour_record_affiche()

        self.construire_grille(lignes, colonnes)

        self.donnees["derniere_difficulte"] = self.difficulte_var.get()
        self.donnees["partie_en_cours"] = None
        sauvegarder_donnees(self.donnees)

        self.demarrer_chrono()

    def reprendre_partie(self, sauvegarde):
        """Restaure une partie précédemment sauvegardée. En cas de
        données invalides, on démarre simplement une nouvelle partie."""
        try:
            difficulte = sauvegarde["difficulte"]
            lignes, colonnes = DIFFICULTES[difficulte]["lignes"], DIFFICULTES[difficulte]["colonnes"]
            symboles = sauvegarde["symboles"]
            trouvees = sauvegarde["trouvees"]
            if len(symboles) != lignes * colonnes or len(trouvees) != len(symboles):
                raise ValueError("Sauvegarde incohérente")

            self.difficulte_var.set(difficulte)
            self.symboles_grille = symboles
            self.cartes_trouvees = trouvees
            self.nombre_coups = sauvegarde["coups"]
            self.temps_ecoule = sauvegarde["temps"]
        except (KeyError, ValueError):
            self.donnees["partie_en_cours"] = None
            self.nouvelle_partie()
            return

        self.cartes_retournees = []
        self.clic_bloque = False
        self.partie_terminee = False

        self.label_difficulte_jeu.config(text=f"Difficulté : {difficulte}")
        self.label_coups.config(text=f"Coups : {self.nombre_coups}")
        self.label_chrono.config(text=f"Temps : {self.temps_ecoule} s")
        self.mettre_a_jour_record_affiche()

        self.construire_grille(lignes, colonnes)

        self.demarrer_chrono()

    def construire_grille(self, lignes, colonnes):
        """(Re)crée les boutons de la grille en fonction de l'état actuel
        de self.symboles_grille / self.cartes_trouvees."""
        for bouton in self.boutons:
            bouton.destroy()
        self.boutons = []

        index = 0
        for ligne in range(lignes):
            for colonne in range(colonnes):
                trouvee = self.cartes_trouvees[index]
                couleur = COULEUR_TROUVEE if trouvee else COULEUR_CACHEE
                bouton = tk.Button(
                    self.cadre_grille,
                    text=self.symboles_grille[index] if trouvee else SYMBOLE_DOS_CARTE,
                    font=POLICE_CARTE,
                    width=4,
                    height=2,
                    bg=couleur,
                    activebackground=couleur,
                    relief="flat",
                    bd=0,
                    command=lambda i=index: self.clic_sur_carte(i),
                )
                bouton.grid(row=ligne, column=colonne, padx=4, pady=4)
                self.boutons.append(bouton)
                index += 1

    # ----- Chronomètre -----

    def demarrer_chrono(self):
        self.id_chrono = self.fenetre.after(1000, self.tick_chrono)

    def arreter_chrono(self):
        if self.id_chrono is not None:
            self.fenetre.after_cancel(self.id_chrono)
            self.id_chrono = None

    def tick_chrono(self):
        self.temps_ecoule += 1
        self.label_chrono.config(text=f"Temps : {self.temps_ecoule} s")
        self.id_chrono = self.fenetre.after(1000, self.tick_chrono)

    # ----- Logique du jeu -----

    def clic_sur_carte(self, index):
        """Appelée lorsque le joueur clique sur la carte numéro `index`."""
        if self.partie_terminee or self.clic_bloque:
            return
        if self.cartes_trouvees[index] or index in self.cartes_retournees:
            return
        if len(self.cartes_retournees) >= 2:
            return

        self.boutons[index].config(
            text=self.symboles_grille[index], bg=COULEUR_DECOUVERTE, activebackground=COULEUR_DECOUVERTE,
        )
        self.cartes_retournees.append(index)

        if len(self.cartes_retournees) == 2:
            self.nombre_coups += 1
            self.label_coups.config(text=f"Coups : {self.nombre_coups}")
            self.clic_bloque = True
            self.fenetre.after(300, self.verifier_paire)

    def verifier_paire(self):
        """Compare les deux cartes retournées et agit en conséquence."""
        index1, index2 = self.cartes_retournees

        if self.symboles_grille[index1] == self.symboles_grille[index2]:
            self.cartes_trouvees[index1] = True
            self.cartes_trouvees[index2] = True
            self.boutons[index1].config(bg=COULEUR_TROUVEE, activebackground=COULEUR_TROUVEE)
            self.boutons[index2].config(bg=COULEUR_TROUVEE, activebackground=COULEUR_TROUVEE)
            self.cartes_retournees = []
            self.clic_bloque = False

            if all(self.cartes_trouvees):
                self.terminer_partie()
        else:
            self.fenetre.after(DELAI_RETOURNEMENT_MS, self.recacher_cartes)

    def recacher_cartes(self):
        """Recache les deux cartes qui ne correspondaient pas."""
        for index in self.cartes_retournees:
            self.boutons[index].config(
                text=SYMBOLE_DOS_CARTE, bg=COULEUR_CACHEE, activebackground=COULEUR_CACHEE,
            )
        self.cartes_retournees = []
        self.clic_bloque = False

    # ----- Fin de partie / sauvegarde des résultats -----

    def terminer_partie(self):
        self.partie_terminee = True
        self.arreter_chrono()
        self.enregistrer_resultat()
        self.fenetre.after(200, self.afficher_victoire)

    def enregistrer_resultat(self):
        difficulte = self.difficulte_var.get()

        records = self.donnees.setdefault("records", {})
        record = records.get(difficulte)
        self.dernier_resultat_est_record = False
        if record is None or self.nombre_coups < record["meilleurs_coups"] or (
            self.nombre_coups == record["meilleurs_coups"] and self.temps_ecoule < record["meilleur_temps"]
        ):
            records[difficulte] = {"meilleurs_coups": self.nombre_coups, "meilleur_temps": self.temps_ecoule}
            self.dernier_resultat_est_record = True

        historique = self.donnees.setdefault("historique", [])
        historique.insert(0, {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "difficulte": difficulte,
            "coups": self.nombre_coups,
            "temps": self.temps_ecoule,
        })
        del historique[TAILLE_HISTORIQUE:]

        stats = self.donnees.setdefault(
            "statistiques", {"parties_terminees": 0, "total_coups": 0, "total_temps": 0}
        )
        stats["parties_terminees"] += 1
        stats["total_coups"] += self.nombre_coups
        stats["total_temps"] += self.temps_ecoule

        self.donnees["partie_en_cours"] = None
        sauvegarder_donnees(self.donnees)

    def afficher_victoire(self):
        message = f"Vous avez trouvé toutes les paires en {self.nombre_coups} coups et {self.temps_ecoule} secondes ! 🎉"
        if self.dernier_resultat_est_record:
            message += "\n\n🌟 Nouveau record pour cette difficulté !"
        messagebox.showinfo("Bravo !", message)
        self.mettre_a_jour_record_affiche()

    # ----- Statistiques (écran intégré à la fenêtre) -----

    def afficher_statistiques(self, origine="menu"):
        """Construit et affiche l'écran de statistiques, dans la même
        fenêtre. `origine` indique quel écran afficher au retour."""
        self.ecran_precedent = origine

        for widget in self.cadre_stats.winfo_children():
            widget.destroy()

        creer_bouton(self.cadre_stats, "🏠 Retour", self.retour_depuis_stats).pack(anchor="w", pady=(0, 10))

        tk.Label(
            self.cadre_stats, text="📊 Statistiques", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND,
        ).pack(pady=(0, 10))

        stats = self.donnees.get("statistiques", {"parties_terminees": 0, "total_coups": 0, "total_temps": 0})
        parties = stats.get("parties_terminees", 0)
        moyenne_coups = stats["total_coups"] / parties if parties else 0
        moyenne_temps = stats["total_temps"] / parties if parties else 0

        tk.Label(self.cadre_stats, text=f"Parties terminées : {parties}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Moyenne de coups : {moyenne_coups:.1f}", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        tk.Label(self.cadre_stats, text=f"Temps moyen : {moyenne_temps:.1f} s", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(0, 10))

        tk.Label(self.cadre_stats, text="🏆 Records par difficulté :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x")
        records = self.donnees.get("records", {})
        if records:
            for difficulte, record in records.items():
                tk.Label(
                    self.cadre_stats,
                    text=f"{difficulte} : {record['meilleurs_coups']} coups en {record['meilleur_temps']} s",
                    font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w",
                ).pack(fill="x", padx=15)
        else:
            tk.Label(self.cadre_stats, text="Aucun record pour l'instant", font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", padx=15)

        tk.Label(self.cadre_stats, text="🕘 Historique récent :", font=POLICE_INFO, fg=COULEUR_TEXTE, bg=COULEUR_FOND, anchor="w").pack(fill="x", pady=(10, 0))
        zone_texte = tk.Text(self.cadre_stats, width=42, height=10, font=POLICE_TEXTE, bg="#fff8fb", fg=COULEUR_TEXTE, relief="flat", bd=6)
        historique = self.donnees.get("historique", [])
        if historique:
            for partie in historique:
                zone_texte.insert(
                    tk.END,
                    f"{partie['date']} - {partie['difficulte']} - {partie['coups']} coups - {partie['temps']} s\n",
                )
        else:
            zone_texte.insert(tk.END, "Aucune partie terminée pour l'instant.")
        zone_texte.config(state="disabled")
        zone_texte.pack(pady=10)

        self.masquer_tous_les_ecrans()
        self.cadre_stats.pack(padx=20, pady=20)

    def retour_depuis_stats(self):
        if self.ecran_precedent == "jeu":
            self.afficher_ecran_jeu()
        else:
            self.afficher_menu()

    # ----- Règles du jeu (écran intégré à la fenêtre) -----

    def construire_ecran_regles(self):
        """Crée une seule fois l'écran des règles (contenu fixe)."""
        creer_bouton(self.cadre_regles, "🏠 Retour", self.afficher_menu).pack(anchor="w", pady=(0, 10))
        tk.Label(
            self.cadre_regles, text="📖 Règles du jeu", font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND,
        ).pack(pady=(0, 10))
        tk.Label(
            self.cadre_regles, text=REGLES_DU_JEU, justify="left", wraplength=340,
            font=POLICE_TEXTE, fg=COULEUR_TEXTE, bg=COULEUR_FOND,
        ).pack()

    def afficher_regles(self):
        self.masquer_tous_les_ecrans()
        self.cadre_regles.pack(padx=25, pady=20)

    # ----- Sauvegarde / fermeture -----

    def sauvegarder_partie_en_cours(self):
        """Enregistre l'état de la partie en cours sur le disque si elle
        n'est pas terminée, pour pouvoir la reprendre plus tard."""
        if not self.partie_terminee and hasattr(self, "symboles_grille"):
            self.donnees["partie_en_cours"] = {
                "difficulte": self.difficulte_var.get(),
                "symboles": self.symboles_grille,
                "trouvees": self.cartes_trouvees,
                "coups": self.nombre_coups,
                "temps": self.temps_ecoule,
            }
            sauvegarder_donnees(self.donnees)

    def fermer_fenetre(self):
        """Sauvegarde la partie en cours (si besoin) avant de fermer la
        fenêtre, pour pouvoir la reprendre plus tard."""
        self.arreter_chrono()
        self.sauvegarder_partie_en_cours()
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    jeu = JeuMemoire(fenetre_principale)
    fenetre_principale.mainloop()
