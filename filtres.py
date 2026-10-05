"""
filtres.py

Structures de donnees representant l'ensemble des criteres de recherche
saisis par l'utilisateur dans l'onglet "Recherche" de app.py. Ces structures
servent de contrat de passage entre l'interface Streamlit, les connecteurs
(connecteurs/*.py) et le module de scoring (scoring.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ModeAffichage(str, Enum):
    '''Mode d'affichage des resultats dans l'onglet Resultats.

    - MELANGE : toutes les annonces, tous sites confondus, triees ensemble
      par score "bonne affaire" (vue rapide, une seule liste).
    - SEPARE : un bloc de resultats distinct par site (vue comparative,
      utile pour comparer precisement l'offre Le Bon Coin vs Vinted).
    '''

    MELANGE = "melange"
    SEPARE = "separe"


class PresetAffichage(str, Enum):
    '''Presets proposes a l'utilisateur pour configurer rapidement le mode d'affichage.

    TODO (V1 - app.py): proposer ces deux presets sous forme de boutons/radio
    au-dessus du choix detaille mode mélangé/separe, afin de simplifier
    l'usage courant :
    - VUE_RAPIDE : equivaut a ModeAffichage.MELANGE, tri unique par score.
    - VUE_COMPARATIVE : equivaut a ModeAffichage.SEPARE, un bloc par site.
    L'utilisateur garde la possibilite de choisir manuellement le mode
    d'affichage sans passer par un preset.
    '''

    VUE_RAPIDE = "vue_rapide"
    VUE_COMPARATIVE = "vue_comparative"


@dataclass
class VilleRayon:
    '''Une zone de recherche geographique : une ville/code postal + un rayon en km.'''

    ville_ou_code_postal: str
    rayon_km: int = 15  # Valeur par defaut raisonnable ; borne UI attendue : 1 a 100 km

    def __post_init__(self) -> None:
        '''Valide que le rayon reste dans les bornes attendues par l'UI (1-100 km).

        Leve une ValueError si ville_ou_code_postal est vide (ou uniquement
        compose d'espaces), ou si rayon_km n'est pas un nombre strictement
        positif.
        '''
        if not isinstance(self.ville_ou_code_postal, str) or not self.ville_ou_code_postal.strip():
            raise ValueError("Le champ ville ou code postal ne peut pas être vide.")
        if not isinstance(self.rayon_km, (int, float)) or isinstance(self.rayon_km, bool) or self.rayon_km <= 0:
            raise ValueError("Le rayon (km) doit être un nombre strictement positif.")


@dataclass
class FiltresRecherche:
    '''Ensemble complet des criteres de recherche choisis par l'utilisateur.

    Cette dataclass est construite dans app.py a partir des widgets Streamlit
    de l'onglet "Recherche", puis transmise aux connecteurs (qui n'utilisent
    que les champs qu'ils savent traiter nativement) et aux modules
    distance.py / scoring.py pour affiner et classer les resultats.
    '''

    # --- Critere produit ---
    mot_cle: str = ""
    prix_min: float | None = None
    prix_max: float | None = None
    etat_minimum: str | None = None  # Valeur attendue : un libelle de connecteurs.base.EtatProduit

    mots_cles_inclus: list[str] = field(default_factory=list)  # Doivent apparaitre dans le titre/description
    mots_cles_exclus: list[str] = field(default_factory=list)  # Ne doivent PAS apparaitre

    # --- Critere geographique ---
    villes_rayons: list[VilleRayon] = field(default_factory=list)
    accepter_si_livraison_disponible: bool = True  # Si True, inclut en "Resultats" une annonce
                                                     # hors rayon mais livrable (sinon -> "Autres")

    # --- Sites a interroger ---
    multisite: bool = True            # Case "Multisite" cochee par defaut : interroge tous les sites actifs
    sites_actifs: list[str] = field(default_factory=lambda: ["leboncoin", "vinted"])  # Utilise si multisite=False

    # --- Vendeur ---
    seuil_fiabilite_vendeur_min: float | None = None  # 0-100 ; None = pas de filtre sur la fiabilite

    # --- Affichage ---
    mode_affichage: ModeAffichage = ModeAffichage.MELANGE

    def sites_a_interroger(self) -> list[str]:
        '''Renvoie la liste finale des sites a interroger, selon multisite et sites_actifs.

        TODO (V1):
        - Si self.multisite est True -> renvoyer la liste de tous les sites
          disponibles dans l'application (ex. ["leboncoin", "vinted"], a
          etendre en V3 avec "facebook_marketplace").
        - Sinon -> renvoyer self.sites_actifs (sites explicitement coches par
          l'utilisateur).
        '''
        raise NotImplementedError("A implementer en V1")

    def valider(self) -> list[str]:
        '''Verifie la coherence globale des filtres et renvoie une liste de messages d'erreur.

        Verifie notamment que prix_min <= prix_max si les deux sont fournis,
        qu'au moins un site est selectionne (selon multisite/sites_actifs),
        et que villes_rayons n'est pas vide si la livraison n'est pas
        acceptee comme alternative. Retourne une liste vide si tout est
        coherent (permet a app.py d'afficher des messages d'erreur clairs
        dans le formulaire).
        '''
        erreurs: list[str] = []

        if self.prix_min is not None and self.prix_max is not None:
            if self.prix_min > self.prix_max:
                erreurs.append("Le prix minimum ne peut pas etre superieur au prix maximum.")

        if self.multisite:
            if not ["leboncoin", "vinted"]:
                erreurs.append("Aucun site disponible a interroger.")
        else:
            if not self.sites_actifs:
                erreurs.append("Veuillez selectionner au moins un site a interroger.")

        if not self.villes_rayons and not self.accepter_si_livraison_disponible:
            erreurs.append(
                "Veuillez ajouter au moins une zone de recherche (ville + rayon) "
                "ou accepter les annonces livrables."
            )

        return erreurs
