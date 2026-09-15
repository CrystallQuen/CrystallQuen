"""
Salle de Jeux Kawaii en Python avec Tkinter.

Un petit menu d'accueil qui liste tous les jeux présents dans ce
dossier. On clique sur un jeu pour le lancer : il s'ouvre dans sa
propre fenêtre, et l'accueil se cache le temps d'y jouer. Dès qu'on
quitte le jeu (bouton « Quitter »/« Menu principal » ou simplement en
fermant sa fenêtre), l'accueil réapparaît automatiquement pour choisir
un autre jeu.

Chaque jeu reste un script Python totalement indépendant (rien n'est
modifié dans les autres fichiers) : cette salle de jeux se contente de
les lancer comme des programmes séparés, avec le même interpréteur
Python que celui utilisé pour la lancer elle-même.
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

# ----- Palette de couleurs « kawaii » -----
COULEUR_FOND = "#fff0f6"
COULEUR_TITRE = "#d6336c"
COULEUR_TEXTE = "#7c4a9e"
COULEUR_BOUTON = "#f48fb1"
COULEUR_BOUTON_SURVOL = "#f76fa0"

POLICE_TITRE = ("Comic Sans MS", 24, "bold")
POLICE_SOUS_TITRE = ("Comic Sans MS", 11, "italic")
POLICE_CARTE_TITRE = ("Comic Sans MS", 13, "bold")
POLICE_CARTE_DESCRIPTION = ("Comic Sans MS", 9)
POLICE_BOUTON = ("Comic Sans MS", 11, "bold")

NB_COLONNES_GRILLE = 3

# Informations « jolies » pour les jeux déjà connus de cette salle de
# jeux (titre, icône, courte description). Un fichier .py présent dans
# le dossier mais absent de cette liste est quand même affiché, avec
# un titre déduit de son nom de fichier et une icône générique : pas
# besoin de modifier ce script pour qu'un nouveau jeu apparaisse.
JEUX_CONNUS = {
    "memory_game.py": {
        "titre": "Jeu de Mémoire", "icone": "🧠",
        "description": "Retrouve toutes les paires de cartes",
    },
    "flappy_bird_kawaii.py": {
        "titre": "Flappy Bird Kawaii", "icone": "🐣",
        "description": "Vole entre les tuyaux sans les toucher",
    },
    "pacman_kawaii.py": {
        "titre": "Pac-Man Kawaii", "icone": "👻",
        "description": "Mange les gommes, évite les fantômes",
    },
    "tetris_kawaii.py": {
        "titre": "Tetris Kawaii", "icone": "🧱",
        "description": "Empile les pièces, complète des lignes",
    },
    "snake_kawaii.py": {
        "titre": "Snake Kawaii", "icone": "🐍",
        "description": "Grandis sans te mordre la queue",
    },
    "fruit_ninja_kawaii.py": {
        "titre": "Fruit Ninja Kawaii", "icone": "🍉",
        "description": "Tranche les fruits, évite les bombes",
    },
    "mario_kart_kawaii.py": {
        "titre": "Mario Kart Kawaii", "icone": "🏎️",
        "description": "Course en pseudo-3D, 3 tours de circuit",
    },
}

# Fichiers à ignorer même s'ils se terminent par .py (scripts utilitaires,
# pas des jeux à proprement parler).
PREFIXES_IGNORES = ("test_", "generer_", "_")


def lister_scripts_python(dossier):
    """Renvoie les noms des fichiers .py directement dans `dossier`
    (sans descendre plus bas), à l'exclusion des scripts ignorés."""
    try:
        noms = os.listdir(dossier)
    except OSError:
        return []
    return [
        nom for nom in noms
        if nom.endswith(".py") and not nom.startswith(PREFIXES_IGNORES)
    ]


def decouvrir_jeux():
    """Cherche tous les jeux (.py) présents dans ce dossier — soit
    directement, soit un niveau plus bas dans un sous-dossier (chaque
    jeu peut avoir son propre sous-dossier, avec sa sauvegarde et sa
    musique à côté) — en dehors de ce script lui-même. Renvoie une
    liste de dictionnaires triée par titre, prête à être affichée."""
    dossier = os.path.dirname(os.path.abspath(__file__))
    nom_de_ce_script = os.path.basename(__file__)

    chemins_candidats = []

    for nom_fichier in lister_scripts_python(dossier):
        if nom_fichier != nom_de_ce_script:
            chemins_candidats.append(os.path.join(dossier, nom_fichier))

    for nom_entree in sorted(os.listdir(dossier)):
        sous_dossier = os.path.join(dossier, nom_entree)
        if not os.path.isdir(sous_dossier) or nom_entree.startswith((".", "_")):
            continue
        for nom_fichier in lister_scripts_python(sous_dossier):
            chemins_candidats.append(os.path.join(sous_dossier, nom_fichier))

    jeux = []
    for chemin in chemins_candidats:
        nom_fichier = os.path.basename(chemin)
        info = JEUX_CONNUS.get(nom_fichier, {})
        titre_par_defaut = nom_fichier[:-3].replace("_", " ").title()
        jeux.append({
            "fichier": chemin,
            "titre": info.get("titre", titre_par_defaut),
            "icone": info.get("icone", "🎮"),
            "description": info.get("description", ""),
        })

    jeux.sort(key=lambda jeu: jeu["titre"])
    return jeux


class SalleDeJeux:
    """Classe principale : affiche la grille de jeux et gère leur lancement."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Salle de Jeux Kawaii")
        self.fenetre.configure(bg=COULEUR_FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        self.processus_en_cours = None
        self.id_surveillance = None

        self.cadre_principal = tk.Frame(self.fenetre, bg=COULEUR_FOND)
        self.cadre_principal.pack(padx=30, pady=25)

        self.construire_interface()

    def construire_interface(self):
        for widget in self.cadre_principal.winfo_children():
            widget.destroy()

        tk.Label(
            self.cadre_principal, text="🎮 Salle de Jeux Kawaii 🎮",
            font=POLICE_TITRE, fg=COULEUR_TITRE, bg=COULEUR_FOND,
        ).pack(pady=(0, 2))
        tk.Label(
            self.cadre_principal, text="‧₊˚ Choisis un jeu pour commencer ! ˚₊‧",
            font=POLICE_SOUS_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND,
        ).pack(pady=(0, 20))

        jeux = decouvrir_jeux()

        if not jeux:
            tk.Label(
                self.cadre_principal, text="Aucun jeu trouvé dans ce dossier.",
                font=POLICE_CARTE_TITRE, fg=COULEUR_TEXTE, bg=COULEUR_FOND,
            ).pack(pady=20)
        else:
            cadre_grille = tk.Frame(self.cadre_principal, bg=COULEUR_FOND)
            cadre_grille.pack()
            for index, jeu in enumerate(jeux):
                ligne, colonne = divmod(index, NB_COLONNES_GRILLE)
                self.creer_carte_jeu(cadre_grille, jeu).grid(row=ligne, column=colonne, padx=8, pady=8)

        cadre_bas = tk.Frame(self.cadre_principal, bg=COULEUR_FOND)
        cadre_bas.pack(pady=(20, 0))
        self.creer_bouton(cadre_bas, "🔄 Actualiser", self.construire_interface).pack(side=tk.LEFT, padx=5)
        self.creer_bouton(cadre_bas, "🚪 Quitter", self.fermer_fenetre).pack(side=tk.LEFT, padx=5)

    def creer_carte_jeu(self, parent, jeu):
        """Crée une « carte » cliquable (icône + titre + description)
        pour un jeu, sous la forme d'un gros bouton kawaii."""
        texte = f"{jeu['icone']}\n{jeu['titre']}\n{jeu['description']}"
        return tk.Button(
            parent, text=texte, font=POLICE_CARTE_TITRE, justify="center",
            command=lambda: self.lancer_jeu(jeu),
            bg=COULEUR_BOUTON, fg="#ffffff", activebackground=COULEUR_BOUTON_SURVOL,
            activeforeground="#ffffff", relief="flat", bd=0,
            width=16, height=5, wraplength=140, cursor="hand2",
        )

    def creer_bouton(self, parent, texte, commande):
        return tk.Button(
            parent, text=texte, font=POLICE_BOUTON, command=commande,
            bg=COULEUR_BOUTON, fg="#ffffff", activebackground=COULEUR_BOUTON_SURVOL,
            activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
        )

    # ----- Lancement d'un jeu et retour à l'accueil -----

    def lancer_jeu(self, jeu):
        if self.processus_en_cours is not None:
            return  # un jeu est déjà en cours de lancement, on ignore le double-clic

        try:
            self.processus_en_cours = subprocess.Popen(
                [sys.executable, jeu["fichier"]],
                cwd=os.path.dirname(jeu["fichier"]),
            )
        except OSError as erreur:
            messagebox.showerror("Impossible de lancer le jeu", f"{jeu['titre']} n'a pas pu démarrer :\n{erreur}")
            return

        self.fenetre.withdraw()  # on cache l'accueil pendant qu'on joue
        self.surveiller_processus()

    def surveiller_processus(self):
        """Vérifie régulièrement si le jeu lancé est toujours ouvert ;
        dès qu'il se ferme, on réaffiche l'accueil."""
        if self.processus_en_cours is not None and self.processus_en_cours.poll() is None:
            self.id_surveillance = self.fenetre.after(400, self.surveiller_processus)
            return

        self.processus_en_cours = None
        self.id_surveillance = None
        self.construire_interface()  # au cas où des jeux auraient été ajoutés/retirés entre-temps
        self.fenetre.deiconify()
        self.fenetre.lift()

    # ----- Fermeture -----

    def fermer_fenetre(self):
        if self.id_surveillance is not None:
            self.fenetre.after_cancel(self.id_surveillance)
        # On ne ferme pas de force un jeu éventuellement lancé : il continue
        # de tourner dans sa propre fenêtre même si on quitte l'accueil.
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    salle = SalleDeJeux(fenetre_principale)
    fenetre_principale.mainloop()
