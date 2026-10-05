"""
favoris.py

Gestion locale (fichier JSON) des annonces favorites et des recherches
sauvegardees, pour un usage strictement personnel. Peut etre migre vers
SQLite plus tard si le volume de donnees le justifie, sans impact sur le
reste de l'application (les fonctions ci-dessous constituent la seule porte
d'entree utilisee par app.py).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: Chemin local du fichier de stockage des favoris et recherches sauvegardees.
CHEMIN_FICHIER_FAVORIS = Path(__file__).parent / "data" / "favoris.json"


@dataclass
class RechercheSauvegardee:
    '''Une recherche nommee par l'utilisateur, reutilisable depuis l'onglet Favoris.'''

    nom: str
    filtres_serialises: dict  # Version serialisable (dict) de filtres.FiltresRecherche


def _charger_fichier() -> dict:
    '''Charge le contenu brut du fichier JSON de favoris (ou une structure vide si absent).

    TODO (V1):
    - Si CHEMIN_FICHIER_FAVORIS n'existe pas, retourner une structure par
      defaut, ex. {"annonces_favorites": [], "recherches_sauvegardees": []}.
    - Sinon, lire et parser le JSON (json.load).
    - Prevoir la creation du dossier parent (data/) si necessaire.
    '''
    raise NotImplementedError("A implementer en V2")


def _sauvegarder_fichier(contenu: dict) -> None:
    '''Ecrit la structure complete dans le fichier JSON de favoris (ecrasement).

    TODO (V2): json.dump(contenu, ..., ensure_ascii=False, indent=2).
    '''
    raise NotImplementedError("A implementer en V2")


def ajouter_favori(annonce) -> None:
    '''Ajoute une annonce (connecteurs.base.Annonce) a la liste des favoris.

    TODO (V2):
    - Charger le fichier, verifier que l'annonce (site + id_externe) n'est
      pas deja presente, l'ajouter (sous forme de dict serialisable), puis
      sauvegarder.
    '''
    raise NotImplementedError("A implementer en V2")


def retirer_favori(site: str, id_externe: str) -> None:
    '''Retire une annonce des favoris, identifiee par son site et son id_externe.

    TODO (V2): charger, filtrer la liste des favoris pour exclure cette
    annonce, sauvegarder.
    '''
    raise NotImplementedError("A implementer en V2")


def lister_favoris() -> list[dict]:
    '''Renvoie la liste des annonces favorites enregistrees (sous forme de dicts).

    TODO (V2): charger le fichier et renvoyer contenu["annonces_favorites"].
    '''
    raise NotImplementedError("A implementer en V2")


def sauvegarder_recherche(nom: str, filtres) -> None:
    '''Sauvegarde une recherche nommee (filtres.FiltresRecherche) pour la retrouver plus tard.

    TODO (V2):
    - Serialiser `filtres` en dict (ex. via dataclasses.asdict, en gerant les
      enums -> .value).
    - Charger le fichier, ajouter/remplacer la recherche de meme nom,
      sauvegarder.
    '''
    raise NotImplementedError("A implementer en V2")


def lister_recherches_sauvegardees() -> list[RechercheSauvegardee]:
    '''Renvoie la liste des recherches sauvegardees par l'utilisateur.

    TODO (V2): charger le fichier et reconstruire une liste de
    RechercheSauvegardee a partir de contenu["recherches_sauvegardees"].
    '''
    raise NotImplementedError("A implementer en V2")


def supprimer_recherche_sauvegardee(nom: str) -> None:
    '''Supprime une recherche sauvegardee par son nom.

    TODO (V2): charger, filtrer, sauvegarder.
    '''
    raise NotImplementedError("A implementer en V2")
