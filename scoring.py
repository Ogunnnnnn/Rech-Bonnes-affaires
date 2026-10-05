"""
scoring.py

Calcul du score "bonne affaire" d'une annonce, en comparant son prix au prix
moyen observe pour des produits similaires d'occasion, et eventuellement au
prix moyen du neuf si cette information est disponible.

Version V1 : logique simple basee sur l'echantillon de la recherche courante
(et potentiellement sur l'historique local accumule via historique_prix.py).
Des TODO explicites indiquent les evolutions prevues (V3 : detection de
lots/bundles).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EtiquetteBonneAffaire(str, Enum):
    '''Etiquette qualitative associee a un score, pour affichage simplifie dans l'UI.'''

    TRES_BONNE_AFFAIRE = "tres_bonne_affaire"
    BONNE_AFFAIRE = "bonne_affaire"
    PRIX_CORRECT = "prix_correct"
    CHER = "cher"
    INDETERMINE = "indetermine"  # Pas assez de donnees de comparaison


@dataclass
class ScoreBonneAffaire:
    '''Resultat du calcul de score pour une annonce donnee.'''

    valeur: float                        # Score numerique, ex. % d'ecart par rapport au marche occasion (negatif = moins cher que le marche)
    etiquette: EtiquetteBonneAffaire
    prix_moyen_occasion_reference: float | None = None
    prix_moyen_neuf_reference: float | None = None


def calculer_prix_moyen_occasion(annonces: list) -> float | None:
    '''Calcule le prix moyen d'occasion a partir d'une liste d'Annonce comparables.

    Parametres
    ----------
    annonces : list[connecteurs.base.Annonce]
        Annonces considerees comme comparables entre elles (meme recherche,
        memes mots-cles), utilisees comme echantillon de reference pour
        estimer le prix moyen du marche de l'occasion.

    Retourne
    --------
    float | None
        Le prix moyen (en euros), ou None si la liste est vide.

    TODO (V1):
    - Calculer une simple moyenne arithmetique des annonce.prix.
    - TODO (evolution): exclure les valeurs aberrantes (ex. methode IQR) pour
      eviter qu'une annonce anormalement chere ou anormalement cheap ne
      fausse la moyenne de reference.
    - TODO (V2): combiner cette moyenne "instantanee" avec l'historique
      accumule via historique_prix.py, pour une estimation plus stable dans
      le temps.
    '''
    raise NotImplementedError("A implementer en V1")


def calculer_score_bonne_affaire(
    annonce,
    prix_moyen_occasion: float | None,
    prix_moyen_neuf: float | None = None,
) -> ScoreBonneAffaire:
    '''Calcule le score "bonne affaire" d'une annonce par rapport au marche.

    Parametres
    ----------
    annonce : connecteurs.base.Annonce
        L'annonce a scorer.
    prix_moyen_occasion : float | None
        Prix moyen observe pour des produits comparables d'occasion (voir
        calculer_prix_moyen_occasion), ou None si non calculable.
    prix_moyen_neuf : float | None
        Prix moyen du neuf pour ce type de produit, si connu (saisi
        manuellement ou issu d'une source future). Optionnel en V1.

    Retourne
    --------
    ScoreBonneAffaire

    TODO (V1):
    - Si prix_moyen_occasion est None -> retourner un score INDETERMINE.
    - Sinon, calculer l'ecart relatif :
          ecart = (annonce.prix - prix_moyen_occasion) / prix_moyen_occasion
      (negatif si l'annonce est moins chere que le marche -> bonne affaire).
    - Associer une etiquette qualitative selon des seuils simples, par
      exemple :
          ecart <= -0.30         -> TRES_BONNE_AFFAIRE
          -0.30 < ecart <= -0.10 -> BONNE_AFFAIRE
          -0.10 < ecart <= 0.10  -> PRIX_CORRECT
          ecart > 0.10           -> CHER
      (seuils a affiner apres premiers tests reels).
    - Si prix_moyen_neuf est fourni, on peut enrichir l'etiquette ou ajouter
      une information complementaire (ex. "-60% par rapport au neuf").

    TODO (V3 - lots/bundles): si annonce.nombre_objets_estime > 1 (champ a
    ajouter dans connecteurs/base.py), diviser annonce.prix par ce nombre
    avant de calculer l'ecart, pour comparer un prix "a l'unite" et eviter
    de sous-estimer la bonne affaire d'un lot.
    '''
    raise NotImplementedError("A implementer en V1")


def classer_annonces_par_score(annonces: list) -> list:
    '''Trie une liste d'Annonce par score "bonne affaire" decroissant (meilleure affaire en premier).

    TODO (V1):
    - Calculer prix_moyen_occasion une seule fois pour tout l'echantillon
      (via calculer_prix_moyen_occasion) puis, pour chaque annonce, calculer
      son ScoreBonneAffaire (via calculer_score_bonne_affaire).
    - Trier les annonces selon ScoreBonneAffaire.valeur croissant (plus
      l'ecart est negatif, meilleure est l'affaire), en placant les scores
      INDETERMINE en fin de liste.
    - Retourner la liste triee (peut etre une liste de tuples
      (Annonce, ScoreBonneAffaire) selon le choix d'implementation retenu
      pour l'affichage dans app.py).
    '''
    raise NotImplementedError("A implementer en V1")
