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
    INDETERMINE = "indetermine"  # Pas assez de donnees pour evaluer.


@dataclass
class ScoreBonneAffaire:
    '''Resultat du calcul de score pour une annonce.

    Champs (a deduire du contexte, car tronques dans l'extraction originale) :
    - valeur: float | None  (ecart relatif ou absolu au prix moyen, negatif = bonne affaire)
    - etiquette: EtiquetteBonneAffaire
    - prix_moyen_reference: float | None
    '''
    valeur: float | None
    etiquette: EtiquetteBonneAffaire
    prix_moyen_reference: float | None


def _prix_valide(prix) -> bool:
    '''Retourne True si prix est un nombre valide et strictement positif.'''
    if prix is None:
        return False
    if isinstance(prix, bool):
        return False
    if not isinstance(prix, (int, float)):
        return False
    return prix > 0


def calculer_prix_moyen_occasion(annonces: list) -> float | None:
    '''Calcule le prix moyen d'occasion a partir d'un echantillon d'annonces.

    TODO (V1): moyenne simple des prix de l'echantillon (annonces de la
    recherche courante), en ignorant les valeurs manquantes/invalides.
    Retourne None si l'echantillon est vide ou invalide.
    '''
    if not annonces:
        return None

    prix_valides = [
        annonce.prix for annonce in annonces if _prix_valide(getattr(annonce, "prix", None))
    ]

    if not prix_valides:
        return None

    return sum(prix_valides) / len(prix_valides)


def calculer_score_bonne_affaire(annonce, prix_moyen_occasion: float | None) -> "ScoreBonneAffaire":
    '''Calcule le ScoreBonneAffaire d'une annonce par rapport au prix moyen occasion.

    TODO (V1): comparer annonce.prix a prix_moyen_occasion, calculer un ecart
    relatif, et deduire une EtiquetteBonneAffaire (tres_bonne_affaire,
    bonne_affaire, prix_correct, cher) selon des seuils, ou INDETERMINE si
    prix_moyen_occasion est None.
    '''
    prix_annonce = getattr(annonce, "prix", None)

    if prix_moyen_occasion is None or not _prix_valide(prix_annonce):
        return ScoreBonneAffaire(
            valeur=None,
            etiquette=EtiquetteBonneAffaire.INDETERMINE,
            prix_moyen_reference=prix_moyen_occasion,
        )

    ecart = (prix_annonce - prix_moyen_occasion) / prix_moyen_occasion

    if ecart <= -0.30:
        etiquette = EtiquetteBonneAffaire.TRES_BONNE_AFFAIRE
    elif ecart <= -0.10:
        etiquette = EtiquetteBonneAffaire.BONNE_AFFAIRE
    elif ecart <= 0.10:
        etiquette = EtiquetteBonneAffaire.PRIX_CORRECT
    else:
        etiquette = EtiquetteBonneAffaire.CHER

    return ScoreBonneAffaire(
        valeur=ecart,
        etiquette=etiquette,
        prix_moyen_reference=prix_moyen_occasion,
    )


def classer_annonces_par_score(annonces: list) -> list:
    '''Classe une liste d'annonces brutes par score de "bonne affaire" decroissant
    (meilleure affaire en premier).

    TODO (V1):
    - Calculer prix_moyen_occasion une seule fois pour tout l'echantillon
      (via calculer_prix_moyen_occasion) puis, pour chaque annonce, calculer
      son ScoreBonneAffaire (via calculer_score_bonne_affaire).
    - Trier les annonces selon ScoreBonneAffaire.valeur croissant (plus
      l'ecart est negatif, meilleure est l'affaire), en placant les scores
      INDETERMINE en fin de liste.
    - Retourner la liste triee (peut etre une liste de tuples
      (Annonce, ScoreBonneAffaire) selon le choix d'implementation retenue
      pour l'affichage dans app.py).
    '''
    prix_moyen_occasion = calculer_prix_moyen_occasion(annonces)

    resultats = [
        (annonce, calculer_score_bonne_affaire(annonce, prix_moyen_occasion))
        for annonce in annonces
    ]

    resultats.sort(
        key=lambda item: (item[1].valeur is None, item[1].valeur if item[1].valeur is not None else 0)
    )

    return resultats
