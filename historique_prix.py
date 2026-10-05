"""
historique_prix.py

Stockage local (fichier JSON) de l'historique des prix moyens observes pour
chaque recherche sauvegardee, afin d'alimenter l'onglet "Historique des
prix" (graphique d'evolution dans le temps). Permet de voir si le marche
d'un produit baisse ou augmente, et donc de mieux juger la pertinence d'une
"bonne affaire" ponctuelle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

#: Chemin local du fichier de stockage de l'historique des prix.
CHEMIN_FICHIER_HISTORIQUE = Path(__file__).parent / "data" / "historique_prix.json"


@dataclass
class PointHistorique:
    '''Un point de mesure : le prix moyen observe pour une recherche a une date donnee.'''

    nom_recherche: str
    date: datetime
    prix_moyen: float
    nombre_annonces_echantillon: int  # Taille de l'echantillon utilise pour la moyenne


def _charger_fichier() -> dict:
    '''Charge le contenu brut du fichier JSON d'historique (ou une structure vide si absent).

    TODO (V2): structure suggeree : {"points": [...]}, chaque point etant un
    dict serialisable correspondant a un PointHistorique.
    '''
    raise NotImplementedError("A implementer en V2")


def _sauvegarder_fichier(contenu: dict) -> None:
    '''Ecrit la structure complete dans le fichier JSON d'historique (ecrasement).

    TODO (V2): json.dump(contenu, ..., ensure_ascii=False, indent=2, default=str).
    '''
    raise NotImplementedError("A implementer en V2")


def enregistrer_point_historique(
    nom_recherche: str,
    prix_moyen: float,
    nombre_annonces_echantillon: int,
    date: datetime | None = None,
) -> None:
    '''Enregistre un nouveau point de mesure dans l'historique local.

    Parametres
    ----------
    nom_recherche : str
        Nom de la recherche sauvegardee (doit correspondre a une entree de
        favoris.lister_recherches_sauvegardees() pour rester coherent).
    prix_moyen : float
        Prix moyen calcule par scoring.calculer_prix_moyen_occasion lors de
        cette recherche.
    nombre_annonces_echantillon : int
        Nombre d'annonces ayant servi a calculer ce prix moyen (indicateur de
        fiabilite du point : un echantillon tres petit est moins fiable).
    date : datetime, optionnel
        Date du point ; par defaut datetime.now() si non fournie.

    TODO (V2): construire le PointHistorique, charger le fichier, ajouter le
    point a la liste, sauvegarder.
    '''
    raise NotImplementedError("A implementer en V2")


def charger_historique(nom_recherche: str) -> list[PointHistorique]:
    '''Renvoie tous les points d'historique enregistres pour une recherche donnee,
    tries par date croissante (pour tracer un graphique d'evolution).

    TODO (V2): charger le fichier, filtrer les points dont nom_recherche
    correspond, les trier par date, les retourner.
    '''
    raise NotImplementedError("A implementer en V2")
