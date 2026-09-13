"""
Flappy Bird Kawaii en Python avec Tkinter.

Un petit oisillon pastel doit voler entre des piliers de bonbon sans
les toucher. Cliquez (ou appuyez sur Espace) pour lui faire battre des
ailes et prendre de l'altitude : la gravité le fait redescendre en
continu, comme dans le Flappy Bird original.
"""

import json
import os
import random
import tkinter as tk

# ----- Constantes de la fenêtre et de la physique -----

LARGEUR_FENETRE = 400
HAUTEUR_FENETRE = 600
HAUTEUR_SOL = 60

GRAVITE = 0.5              # accélération verticale appliquée à chaque image
FORCE_SAUT = -8.5           # vitesse verticale donnée à l'oiseau à chaque battement d'ailes
VITESSE_MAX_CHUTE = 10

VITESSE_DEFILEMENT = 3      # vitesse de déplacement des tuyaux vers la gauche
LARGEUR_TUYAU = 70
ECART_TUYAU = 165           # hauteur du passage entre le tuyau du haut et celui du bas
ESPACE_ENTRE_TUYAUX = 230   # distance horizontale entre deux paires de tuyaux

RAYON_OISEAU = 18
OISEAU_X = 100               # l'oiseau reste toujours à la même position horizontale

DELAI_BOUCLE_MS = 16  # ~60 images par seconde

# ----- Palette de couleurs « kawaii » (tons pastel) -----
COULEUR_CIEL_HAUT = "#bdeaff"
COULEUR_CIEL_BAS = "#e8f7ff"
COULEUR_NUAGE = "#ffffff"
COULEUR_NUAGE_CONTOUR = "#ffd6ec"
COULEUR_SOL = "#ffe3b3"
COULEUR_HERBE = "#b8e8b0"
COULEUR_TUYAU = "#c9a8ff"
COULEUR_TUYAU_BORD = "#a78bfa"
COULEUR_OISEAU_CORPS = "#fff3b0"
COULEUR_OISEAU_AILE = "#ffe27a"
COULEUR_OISEAU_BEC = "#ffb74d"
COULEUR_OISEAU_JOUE = "#ffb6d9"
COULEUR_TEXTE = "#7c4a9e"
COULEUR_TITRE = "#d6336c"
COULEUR_BOUTON = "#f48fb1"
COULEUR_BOUTON_SURVOL = "#f76fa0"

POLICE_TITRE = ("Comic Sans MS", 22, "bold")
POLICE_SCORE = ("Comic Sans MS", 26, "bold")
POLICE_INFO = ("Comic Sans MS", 13, "bold")
POLICE_BOUTON = ("Comic Sans MS", 13, "bold")

# Fichier de sauvegarde du meilleur score, créé à côté de ce script.
FICHIER_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "flappy_kawaii_sauvegarde.json"
)


def charger_meilleur_score():
    """Lit le meilleur score enregistré, ou 0 si le fichier n'existe
    pas encore / est illisible."""
    if not os.path.exists(FICHIER_SAUVEGARDE):
        return 0
    try:
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as fichier:
            return int(json.load(fichier).get("meilleur_score", 0))
    except (json.JSONDecodeError, OSError, ValueError):
        return 0


def sauvegarder_meilleur_score(score):
    try:
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as fichier:
            json.dump({"meilleur_score": score}, fichier)
    except OSError:
        pass  # pas grave si la sauvegarde échoue, le jeu continue quand même


def interpoler_couleur(couleur1, couleur2, proportion):
    """Mélange deux couleurs hexadécimales (#rrggbb) selon `proportion`
    (0 = couleur1, 1 = couleur2). Sert à dessiner un ciel en dégradé."""
    r1, v1, b1 = int(couleur1[1:3], 16), int(couleur1[3:5], 16), int(couleur1[5:7], 16)
    r2, v2, b2 = int(couleur2[1:3], 16), int(couleur2[3:5], 16), int(couleur2[5:7], 16)
    r = round(r1 + (r2 - r1) * proportion)
    v = round(v1 + (v2 - v1) * proportion)
    b = round(b1 + (b2 - b1) * proportion)
    return f"#{r:02x}{v:02x}{b:02x}"


class JeuFlappy:
    """Classe principale qui gère la fenêtre, le décor et la logique du jeu."""

    def __init__(self, fenetre):
        self.fenetre = fenetre
        self.fenetre.title("Flappy Bird Kawaii")
        self.fenetre.resizable(False, False)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer_fenetre)

        self.meilleur_score = charger_meilleur_score()

        self.canvas = tk.Canvas(
            fenetre, width=LARGEUR_FENETRE, height=HAUTEUR_FENETRE, highlightthickness=0,
        )
        self.canvas.pack()

        self.canvas.bind("<Button-1>", lambda evenement: self.on_action())
        self.fenetre.bind("<space>", lambda evenement: self.on_action())

        self.id_boucle = None
        self.bouton_rejouer = None

        self.nouvelle_partie()

    # ----- Décor (dessiné une seule fois par partie, ne bouge pas) -----

    def dessiner_ciel(self):
        nb_bandes = 24
        for i in range(nb_bandes):
            proportion = i / (nb_bandes - 1)
            couleur = interpoler_couleur(COULEUR_CIEL_HAUT, COULEUR_CIEL_BAS, proportion)
            y0 = i * HAUTEUR_FENETRE / nb_bandes
            y1 = (i + 1) * HAUTEUR_FENETRE / nb_bandes
            self.canvas.create_rectangle(0, y0, LARGEUR_FENETRE, y1, fill=couleur, outline=couleur)

    def dessiner_nuage(self, x, y, echelle=1.0):
        for dx, dy, largeur, hauteur in [(0, 0, 40, 24), (18, -10, 40, 26), (36, 0, 40, 22)]:
            largeur, hauteur = largeur * echelle, hauteur * echelle
            self.canvas.create_oval(
                x + dx, y + dy, x + dx + largeur, y + dy + hauteur,
                fill=COULEUR_NUAGE, outline=COULEUR_NUAGE_CONTOUR, width=2,
            )

    def dessiner_soleil(self, x, y, rayon):
        self.canvas.create_oval(x - rayon, y - rayon, x + rayon, y + rayon, fill="#fff3b0", outline="#ffe07a", width=3)
        self.canvas.create_oval(x - 8, y - 4, x - 4, y, fill=COULEUR_TEXTE, outline="")
        self.canvas.create_oval(x + 4, y - 4, x + 8, y, fill=COULEUR_TEXTE, outline="")
        self.canvas.create_arc(x - 8, y - 2, x + 8, y + 10, start=200, extent=140, style="arc", outline=COULEUR_TEXTE, width=2)
        self.canvas.create_oval(x - 14, y + 2, x - 8, y + 7, fill=COULEUR_OISEAU_JOUE, outline="")
        self.canvas.create_oval(x + 8, y + 2, x + 14, y + 7, fill=COULEUR_OISEAU_JOUE, outline="")

    def dessiner_sol(self):
        y_sol = HAUTEUR_FENETRE - HAUTEUR_SOL
        self.canvas.create_rectangle(0, y_sol, LARGEUR_FENETRE, HAUTEUR_FENETRE, fill=COULEUR_SOL, outline="")
        self.canvas.create_rectangle(0, y_sol, LARGEUR_FENETRE, y_sol + 14, fill=COULEUR_HERBE, outline="")
        for x in range(0, LARGEUR_FENETRE, 20):
            self.canvas.create_polygon(x, y_sol + 14, x + 10, y_sol + 2, x + 20, y_sol + 14, fill=COULEUR_HERBE, outline="")

    def dessiner_decor(self):
        self.dessiner_ciel()
        self.dessiner_nuage(50, 80)
        self.dessiner_nuage(240, 50, 0.8)
        self.dessiner_nuage(140, 150, 0.6)
        self.dessiner_soleil(350, 60, 26)
        self.dessiner_sol()

    # ----- L'oiseau -----

    def creer_oiseau(self, x, y):
        """Crée les éléments graphiques de l'oiseau et renvoie leurs identifiants."""
        r = RAYON_OISEAU
        corps = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=COULEUR_OISEAU_CORPS, outline="#f4c95d", width=2)
        aile = self.canvas.create_oval(x - r * 0.6, y - 2, x + r * 0.1, y + r * 0.6, fill=COULEUR_OISEAU_AILE, outline="")
        bec = self.canvas.create_polygon(x + r - 4, y, x + r + 9, y - 3, x + r + 9, y + 5, fill=COULEUR_OISEAU_BEC, outline="")
        oeil = self.canvas.create_oval(x + 3, y - 9, x + 11, y - 1, fill="#4a3f35", outline="")
        reflet = self.canvas.create_oval(x + 7, y - 8, x + 9, y - 6, fill="#ffffff", outline="")
        joue = self.canvas.create_oval(x - 3, y + 2, x + 5, y + 8, fill=COULEUR_OISEAU_JOUE, outline="")
        return [corps, aile, bec, oeil, reflet, joue]

    # ----- Texte avec un petit contour (effet « bande dessinée ») -----

    def creer_texte_contour(self, x, y, texte, police, couleur):
        ids_contour = []
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            ids_contour.append(self.canvas.create_text(x + dx, y + dy, text=texte, font=police, fill="#ffffff"))
        id_principal = self.canvas.create_text(x, y, text=texte, font=police, fill=couleur)
        return ids_contour + [id_principal]

    def changer_texte(self, ids_texte, nouveau_texte):
        for identifiant in ids_texte:
            self.canvas.itemconfig(identifiant, text=nouveau_texte)

    # ----- Tuyaux (obstacles) -----

    def creer_tuyau(self, x, centre_ecart):
        bas_du_haut = centre_ecart - ECART_TUYAU / 2
        haut_du_bas = centre_ecart + ECART_TUYAU / 2
        y_sol = HAUTEUR_FENETRE - HAUTEUR_SOL

        id_haut = self.canvas.create_rectangle(x, 0, x + LARGEUR_TUYAU, bas_du_haut, fill=COULEUR_TUYAU, outline=COULEUR_TUYAU_BORD, width=2)
        id_bas = self.canvas.create_rectangle(x, haut_du_bas, x + LARGEUR_TUYAU, y_sol, fill=COULEUR_TUYAU, outline=COULEUR_TUYAU_BORD, width=2)
        id_bout_haut = self.canvas.create_rectangle(x - 4, bas_du_haut - 16, x + LARGEUR_TUYAU + 4, bas_du_haut, fill=COULEUR_TUYAU_BORD, outline="")
        id_bout_bas = self.canvas.create_rectangle(x - 4, haut_du_bas, x + LARGEUR_TUYAU + 4, haut_du_bas + 16, fill=COULEUR_TUYAU_BORD, outline="")

        return {
            "x": x,
            "centre_ecart": centre_ecart,
            "compte": False,
            "ids": [id_haut, id_bas, id_bout_haut, id_bout_bas],
        }

    def ajouter_tuyau(self):
        marge = 60
        minimum = marge + ECART_TUYAU // 2
        maximum = HAUTEUR_FENETRE - HAUTEUR_SOL - marge - ECART_TUYAU // 2
        centre_ecart = random.randint(minimum, maximum)
        self.tuyaux.append(self.creer_tuyau(LARGEUR_FENETRE, centre_ecart))

    # ----- Préparation d'une nouvelle partie -----

    def nouvelle_partie(self):
        if self.id_boucle is not None:
            self.fenetre.after_cancel(self.id_boucle)
            self.id_boucle = None
        if self.bouton_rejouer is not None:
            self.bouton_rejouer.destroy()
            self.bouton_rejouer = None

        self.canvas.delete("all")
        self.dessiner_decor()

        self.oiseau_y = HAUTEUR_FENETRE / 2
        self.vitesse_y = 0
        self.parties_oiseau = self.creer_oiseau(OISEAU_X, self.oiseau_y)

        self.tuyaux = []
        self.distance_depuis_tuyau = 0
        self.score = 0

        self.ids_score = self.creer_texte_contour(LARGEUR_FENETRE / 2, 40, "0", POLICE_SCORE, COULEUR_TEXTE)

        self.canvas.create_text(
            LARGEUR_FENETRE / 2, 90, text=f"Meilleur score : {self.meilleur_score}",
            font=POLICE_INFO, fill=COULEUR_TITRE,
        )

        self.ids_message_attente = self.creer_texte_contour(
            LARGEUR_FENETRE / 2, HAUTEUR_FENETRE / 2 - 40,
            "🐣 Flappy Bird Kawaii", POLICE_TITRE, COULEUR_TITRE,
        )
        self.ids_message_attente += self.creer_texte_contour(
            LARGEUR_FENETRE / 2, HAUTEUR_FENETRE / 2 + 10,
            "👆 Cliquez ou appuyez sur Espace\npour jouer", POLICE_INFO, COULEUR_TEXTE,
        )

        self.etat = "attente"

    # ----- Entrées du joueur -----

    def on_action(self):
        if self.etat == "attente":
            self.demarrer_partie()
        elif self.etat == "jeu":
            self.sauter()
        # en état "fin", on ignore le clic : il faut utiliser le bouton « Rejouer »

    def sauter(self):
        self.vitesse_y = FORCE_SAUT

    def demarrer_partie(self):
        for identifiant in self.ids_message_attente:
            self.canvas.delete(identifiant)
        self.etat = "jeu"
        self.boucle_jeu()

    # ----- Boucle principale du jeu -----

    def boucle_jeu(self):
        # Physique de l'oiseau : la gravité l'accélère vers le bas.
        self.vitesse_y = min(self.vitesse_y + GRAVITE, VITESSE_MAX_CHUTE)
        nouvelle_y = self.oiseau_y + self.vitesse_y
        if nouvelle_y - RAYON_OISEAU < 0:
            nouvelle_y = RAYON_OISEAU
            self.vitesse_y = 0
        deplacement_y = nouvelle_y - self.oiseau_y
        for identifiant in self.parties_oiseau:
            self.canvas.move(identifiant, 0, deplacement_y)
        self.oiseau_y = nouvelle_y

        # Déplacement des tuyaux vers la gauche.
        for tuyau in self.tuyaux:
            for identifiant in tuyau["ids"]:
                self.canvas.move(identifiant, -VITESSE_DEFILEMENT, 0)
            tuyau["x"] -= VITESSE_DEFILEMENT

            if not tuyau["compte"] and tuyau["x"] + LARGEUR_TUYAU < OISEAU_X:
                tuyau["compte"] = True
                self.score += 1
                self.changer_texte(self.ids_score, str(self.score))

        # On enlève les tuyaux sortis de l'écran à gauche.
        tuyaux_restants = []
        for tuyau in self.tuyaux:
            if tuyau["x"] + LARGEUR_TUYAU < 0:
                for identifiant in tuyau["ids"]:
                    self.canvas.delete(identifiant)
            else:
                tuyaux_restants.append(tuyau)
        self.tuyaux = tuyaux_restants

        # On ajoute un nouveau tuyau quand c'est le moment.
        self.distance_depuis_tuyau += VITESSE_DEFILEMENT
        if self.distance_depuis_tuyau >= ESPACE_ENTRE_TUYAUX:
            self.distance_depuis_tuyau = 0
            self.ajouter_tuyau()

        if self.collision_detectee():
            self.terminer_partie()
            return

        self.id_boucle = self.fenetre.after(DELAI_BOUCLE_MS, self.boucle_jeu)

    def collision_detectee(self):
        y_sol = HAUTEUR_FENETRE - HAUTEUR_SOL
        if self.oiseau_y + RAYON_OISEAU >= y_sol:
            return True

        for tuyau in self.tuyaux:
            chevauchement_horizontal = (
                tuyau["x"] < OISEAU_X + RAYON_OISEAU and tuyau["x"] + LARGEUR_TUYAU > OISEAU_X - RAYON_OISEAU
            )
            if chevauchement_horizontal:
                bas_du_haut = tuyau["centre_ecart"] - ECART_TUYAU / 2
                haut_du_bas = tuyau["centre_ecart"] + ECART_TUYAU / 2
                if self.oiseau_y - RAYON_OISEAU < bas_du_haut or self.oiseau_y + RAYON_OISEAU > haut_du_bas:
                    return True
        return False

    # ----- Fin de partie -----

    def terminer_partie(self):
        self.etat = "fin"
        if self.score > self.meilleur_score:
            self.meilleur_score = self.score
            sauvegarder_meilleur_score(self.meilleur_score)

        cx, cy = LARGEUR_FENETRE / 2, HAUTEUR_FENETRE / 2
        self.canvas.create_rectangle(
            cx - 140, cy - 95, cx + 140, cy + 95, fill="#fff0f6", outline=COULEUR_BOUTON, width=3,
        )
        self.creer_texte_contour(cx, cy - 60, "💔 Partie terminée", POLICE_INFO, COULEUR_TITRE)
        self.creer_texte_contour(cx, cy - 25, f"Score : {self.score}", POLICE_SCORE, COULEUR_TEXTE)
        self.canvas.create_text(cx, cy + 10, text=f"Meilleur score : {self.meilleur_score}", font=POLICE_INFO, fill=COULEUR_TITRE)

        self.bouton_rejouer = tk.Button(
            self.canvas, text="🔄 Rejouer", font=POLICE_BOUTON, command=self.nouvelle_partie,
            bg=COULEUR_BOUTON, fg="#ffffff", activebackground=COULEUR_BOUTON_SURVOL,
            activeforeground="#ffffff", relief="flat", bd=0, padx=16, pady=8, cursor="hand2",
        )
        self.canvas.create_window(cx, cy + 55, window=self.bouton_rejouer)

    # ----- Fermeture -----

    def fermer_fenetre(self):
        if self.id_boucle is not None:
            self.fenetre.after_cancel(self.id_boucle)
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre_principale = tk.Tk()
    jeu = JeuFlappy(fenetre_principale)
    fenetre_principale.mainloop()
