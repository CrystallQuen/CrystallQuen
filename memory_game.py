"""
Jeu de Mémoire (Memory) en Python avec Tkinter.

Règle du jeu : une grille de 16 cartes (8 paires de symboles) est
affichée face cachée. Le joueur clique sur deux cartes ; si elles
correspondent, elles restent visibles, sinon elles se recachent après
une courte pause. Le but est de retrouver toutes les paires en un
minimum de coups.
"""

import random
import tkinter as tk
from tkinter import messagebox

# ----- Constantes de configuration -----
GRILLE_TAILLE = 4  # grille 4x4 -> 16 cartes -> 8 paires
SYMBOLES = ["🍎", "🍌", "🍇", "🍓", "🍒", "🍍", "🥝", "🍑"]

COULEUR_CACHEE = "#4a90d9"      # couleur d'une carte face cachée
COULEUR_DECOUVERTE = "#f5f5f5"  # couleur d'une carte retournée
COULEUR_TROUVEE = "#a5d6a7"     # couleur d'une paire trouvée

DELAI_RETOURNEMENT_MS = 1000  # délai (ms) avant de recacher deux cartes


class JeuMemoire:
    """Classe principale qui gère la fenêtre et la logique du jeu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Jeu de Mémoire")
        self.fenetre.configure(bg="#ffffff")
        self.fenetre.resizable(False, False)

        # Nombre de coups joués par le joueur
        self.nombre_coups = 0

        # Liste des cartes actuellement retournées (contient des index)
        self.cartes_retournees = []

        # Empêche de cliquer pendant l'animation de retournement
        self.clic_bloque = False

        # ----- Zone du haut : compteur de coups et bouton "Nouvelle partie" -----
        cadre_haut = tk.Frame(self.fenetre, bg="#ffffff")
        cadre_haut.pack(pady=10)

        self.label_coups = tk.Label(
            cadre_haut,
            text="Coups : 0",
            font=("Helvetica", 14, "bold"),
            bg="#ffffff",
        )
        self.label_coups.pack(side=tk.LEFT, padx=10)

        bouton_nouvelle_partie = tk.Button(
            cadre_haut,
            text="Nouvelle partie",
            font=("Helvetica", 12),
            command=self.nouvelle_partie,
        )
        bouton_nouvelle_partie.pack(side=tk.LEFT, padx=10)

        # ----- Zone de la grille de cartes -----
        self.cadre_grille = tk.Frame(self.fenetre, bg="#ffffff")
        self.cadre_grille.pack(padx=10, pady=10)

        # Liste des boutons (un par carte) pour pouvoir les modifier facilement
        self.boutons = []

        self.nouvelle_partie()

    def nouvelle_partie(self):
        """Prépare une nouvelle grille mélangée et réinitialise l'état du jeu."""
        self.nombre_coups = 0
        self.label_coups.config(text="Coups : 0")
        self.cartes_retournees = []
        self.clic_bloque = False

        # On crée la liste des symboles : chaque symbole apparaît 2 fois,
        # puis on mélange l'ordre aléatoirement.
        self.symboles_grille = SYMBOLES * 2
        random.shuffle(self.symboles_grille)

        # Cette liste indique, pour chaque carte, si elle a déjà été trouvée
        self.cartes_trouvees = [False] * len(self.symboles_grille)

        # On supprime les anciens boutons de la grille (s'il y en a)
        for bouton in self.boutons:
            bouton.destroy()
        self.boutons = []

        # On crée un bouton pour chaque carte, placé dans la grille
        index = 0
        for ligne in range(GRILLE_TAILLE):
            for colonne in range(GRILLE_TAILLE):
                bouton = tk.Button(
                    self.cadre_grille,
                    text="",
                    font=("Helvetica", 20),
                    width=4,
                    height=2,
                    bg=COULEUR_CACHEE,
                    activebackground=COULEUR_CACHEE,
                    command=lambda i=index: self.clic_sur_carte(i),
                )
                bouton.grid(row=ligne, column=colonne, padx=5, pady=5)
                self.boutons.append(bouton)
                index += 1

    def clic_sur_carte(self, index):
        """Appelée lorsque le joueur clique sur la carte numéro `index`."""
        # On ignore le clic si :
        # - les cartes sont en train d'être recachées (clic_bloque)
        # - la carte est déjà trouvée
        # - la carte est déjà retournée
        if self.clic_bloque:
            return
        if self.cartes_trouvees[index]:
            return
        if index in self.cartes_retournees:
            return
        # On ne peut pas retourner plus de deux cartes à la fois
        if len(self.cartes_retournees) >= 2:
            return

        # On retourne la carte : on affiche son symbole
        self.boutons[index].config(
            text=self.symboles_grille[index], bg=COULEUR_DECOUVERTE
        )
        self.cartes_retournees.append(index)

        # Si c'est la deuxième carte retournée, on vérifie la correspondance
        if len(self.cartes_retournees) == 2:
            self.nombre_coups += 1
            self.label_coups.config(text=f"Coups : {self.nombre_coups}")
            self.clic_bloque = True  # on bloque les clics pendant la vérification
            # On attend un court instant avant de vérifier, pour laisser
            # le joueur voir la deuxième carte retournée.
            self.fenetre.after(300, self.verifier_paire)

    def verifier_paire(self):
        """Compare les deux cartes retournées et agit en conséquence."""
        index1, index2 = self.cartes_retournees

        if self.symboles_grille[index1] == self.symboles_grille[index2]:
            # Les deux cartes correspondent : on les marque comme trouvées
            self.cartes_trouvees[index1] = True
            self.cartes_trouvees[index2] = True
            self.boutons[index1].config(bg=COULEUR_TROUVEE)
            self.boutons[index2].config(bg=COULEUR_TROUVEE)
            self.cartes_retournees = []
            self.clic_bloque = False

            # On vérifie si toutes les paires ont été trouvées
            if all(self.cartes_trouvees):
                self.fenetre.after(200, self.afficher_victoire)
        else:
            # Les cartes ne correspondent pas : on les recache après un délai
            self.fenetre.after(DELAI_RETOURNEMENT_MS, self.recacher_cartes)

    def recacher_cartes(self):
        """Recache les deux cartes qui ne correspondaient pas."""
        for index in self.cartes_retournees:
            self.boutons[index].config(text="", bg=COULEUR_CACHEE)
        self.cartes_retournees = []
        self.clic_bloque = False

    def afficher_victoire(self):
        """Affiche un message de victoire avec le nombre de coups joués."""
        messagebox.showinfo(
            "Bravo !",
            f"Vous avez trouvé toutes les paires en {self.nombre_coups} coups !",
        )


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    jeu = JeuMemoire(fenetre_principale)
    fenetre_principale.mainloop()
