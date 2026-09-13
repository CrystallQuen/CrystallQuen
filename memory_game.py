"""
Jeu de Mémoire (Memory) en Python avec Tkinter.

Règle du jeu : une grille de cartes est affichée face cachée. Le joueur
clique sur deux cartes ; si elles correspondent, elles restent
visibles, sinon elles se recachent après une courte pause. Le but est
de retrouver toutes les paires en un minimum de coups et de temps.

Fonctionnalités :
- Plusieurs niveaux de difficulté (taille de grille différente).
- Chronomètre et compteur de coups.
- Sauvegarde automatique des meilleurs scores et de l'historique des
  parties dans un fichier JSON à côté de ce script.
- Reprise automatique d'une partie interrompue (fermeture de la
  fenêtre en cours de jeu).
- Fenêtre de statistiques (records, moyenne de coups/temps, historique).
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

COULEUR_CACHEE = "#4a90d9"      # couleur d'une carte face cachée
COULEUR_DECOUVERTE = "#f5f5f5"  # couleur d'une carte retournée
COULEUR_TROUVEE = "#a5d6a7"     # couleur d'une paire trouvée

DELAI_RETOURNEMENT_MS = 1000  # délai (ms) avant de recacher deux cartes

# Fichier de sauvegarde, toujours créé à côté de ce script.
FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "memory_sauvegarde.json"
)

# Nombre maximal de parties conservées dans l'historique.
TAILLE_HISTORIQUE = 20


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


class JeuMemoire:
    """Classe principale qui gère la fenêtre et la logique du jeu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Jeu de Mémoire")
        self.fenetre.configure(bg="#ffffff")
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

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

        # ----- Barre du haut : difficulté -----
        cadre_difficulte = tk.Frame(self.fenetre, bg="#ffffff")
        cadre_difficulte.pack(pady=(10, 0))

        tk.Label(cadre_difficulte, text="Difficulté :", bg="#ffffff").pack(side=tk.LEFT, padx=5)

        difficulte_initiale = self.donnees.get("derniere_difficulte") or next(iter(DIFFICULTES))
        self.difficulte_var = tk.StringVar(value=difficulte_initiale)
        selecteur_difficulte = ttk.Combobox(
            cadre_difficulte,
            textvariable=self.difficulte_var,
            values=list(DIFFICULTES.keys()),
            state="readonly",
            width=14,
        )
        selecteur_difficulte.pack(side=tk.LEFT, padx=5)
        selecteur_difficulte.bind("<<ComboboxSelected>>", lambda evenement: self.mettre_a_jour_record_affiche())

        # ----- Barre du haut : coups, chrono, record, boutons -----
        cadre_haut = tk.Frame(self.fenetre, bg="#ffffff")
        cadre_haut.pack(pady=10)

        self.label_coups = tk.Label(cadre_haut, text="Coups : 0", font=("Helvetica", 12, "bold"), bg="#ffffff")
        self.label_coups.pack(side=tk.LEFT, padx=8)

        self.label_chrono = tk.Label(cadre_haut, text="Temps : 0 s", font=("Helvetica", 12, "bold"), bg="#ffffff")
        self.label_chrono.pack(side=tk.LEFT, padx=8)

        self.label_record = tk.Label(cadre_haut, text="Record : aucun", font=("Helvetica", 12), bg="#ffffff")
        self.label_record.pack(side=tk.LEFT, padx=8)

        tk.Button(cadre_haut, text="Nouvelle partie", font=("Helvetica", 11), command=self.demander_nouvelle_partie).pack(side=tk.LEFT, padx=5)
        tk.Button(cadre_haut, text="Statistiques", font=("Helvetica", 11), command=self.afficher_statistiques).pack(side=tk.LEFT, padx=5)

        # ----- Zone de la grille de cartes -----
        self.cadre_grille = tk.Frame(self.fenetre, bg="#ffffff")
        self.cadre_grille.pack(padx=10, pady=10)

        # Si une partie était en cours lors de la dernière fermeture, on
        # propose au joueur de la reprendre.
        partie_sauvee = self.donnees.get("partie_en_cours")
        if partie_sauvee and messagebox.askyesno(
            "Reprendre la partie", "Une partie était en cours. Voulez-vous la reprendre ?"
        ):
            self.reprendre_partie(partie_sauvee)
        else:
            self.donnees["partie_en_cours"] = None
            self.nouvelle_partie()

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
        """Appelée par le bouton « Nouvelle partie » : demande confirmation
        si une partie non terminée risque d'être perdue."""
        if not self.partie_terminee and self.nombre_coups > 0:
            if not messagebox.askyesno(
                "Nouvelle partie", "Une partie est en cours. L'abandonner et en commencer une nouvelle ?"
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
                bouton = tk.Button(
                    self.cadre_grille,
                    text=self.symboles_grille[index] if trouvee else "",
                    font=("Helvetica", 16),
                    width=4,
                    height=2,
                    bg=COULEUR_TROUVEE if trouvee else COULEUR_CACHEE,
                    activebackground=COULEUR_CACHEE,
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

        self.boutons[index].config(text=self.symboles_grille[index], bg=COULEUR_DECOUVERTE)
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
            self.boutons[index1].config(bg=COULEUR_TROUVEE)
            self.boutons[index2].config(bg=COULEUR_TROUVEE)
            self.cartes_retournees = []
            self.clic_bloque = False

            if all(self.cartes_trouvees):
                self.terminer_partie()
        else:
            self.fenetre.after(DELAI_RETOURNEMENT_MS, self.recacher_cartes)

    def recacher_cartes(self):
        """Recache les deux cartes qui ne correspondaient pas."""
        for index in self.cartes_retournees:
            self.boutons[index].config(text="", bg=COULEUR_CACHEE)
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
        message = f"Vous avez trouvé toutes les paires en {self.nombre_coups} coups et {self.temps_ecoule} secondes !"
        if self.dernier_resultat_est_record:
            message += "\n\nNouveau record pour cette difficulté !"
        messagebox.showinfo("Bravo !", message)
        self.mettre_a_jour_record_affiche()

    # ----- Statistiques -----

    def afficher_statistiques(self):
        fenetre_stats = tk.Toplevel(self.fenetre)
        fenetre_stats.title("Statistiques")
        fenetre_stats.configure(bg="#ffffff")
        fenetre_stats.resizable(False, False)

        stats = self.donnees.get("statistiques", {"parties_terminees": 0, "total_coups": 0, "total_temps": 0})
        parties = stats.get("parties_terminees", 0)
        moyenne_coups = stats["total_coups"] / parties if parties else 0
        moyenne_temps = stats["total_temps"] / parties if parties else 0

        tk.Label(fenetre_stats, text=f"Parties terminées : {parties}", bg="#ffffff", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(fenetre_stats, text=f"Moyenne de coups : {moyenne_coups:.1f}", bg="#ffffff", anchor="w").pack(fill="x", padx=10)
        tk.Label(fenetre_stats, text=f"Temps moyen : {moyenne_temps:.1f} s", bg="#ffffff", anchor="w").pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(fenetre_stats, text="Records par difficulté :", font=("Helvetica", 11, "bold"), bg="#ffffff", anchor="w").pack(fill="x", padx=10)
        records = self.donnees.get("records", {})
        if records:
            for difficulte, record in records.items():
                tk.Label(
                    fenetre_stats,
                    text=f"{difficulte} : {record['meilleurs_coups']} coups en {record['meilleur_temps']} s",
                    bg="#ffffff",
                    anchor="w",
                ).pack(fill="x", padx=20)
        else:
            tk.Label(fenetre_stats, text="Aucun record pour l'instant", bg="#ffffff", anchor="w").pack(fill="x", padx=20)

        tk.Label(fenetre_stats, text="Historique récent :", font=("Helvetica", 11, "bold"), bg="#ffffff", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        zone_texte = tk.Text(fenetre_stats, width=42, height=10, font=("Helvetica", 10))
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
        zone_texte.pack(padx=10, pady=10)

    # ----- Fermeture de la fenêtre -----

    def fermer_fenetre(self):
        """Sauvegarde la partie en cours (si elle n'est pas terminée)
        avant de fermer la fenêtre, pour pouvoir la reprendre plus tard."""
        if not self.partie_terminee:
            self.donnees["partie_en_cours"] = {
                "difficulte": self.difficulte_var.get(),
                "symboles": self.symboles_grille,
                "trouvees": self.cartes_trouvees,
                "coups": self.nombre_coups,
                "temps": self.temps_ecoule,
            }
            sauvegarder_donnees(self.donnees)
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    jeu = JeuMemoire(fenetre_principale)
    fenetre_principale.mainloop()
