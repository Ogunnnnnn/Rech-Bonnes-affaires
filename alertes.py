"""
alertes.py

Gestion locale (fichier JSON) des alertes produit : une alerte associe une
recherche sauvegardee (voir favoris.py) a une condition de declenchement
(ex. "prix sous un certain seuil", ou simplement "nouvelle annonce
correspondant aux filtres depuis la derniere consultation").

Important (V1/V2) : aucune notification automatique n'est envoyee (pas de
tache planifiee/serveur en arriere-plan). La verification des alertes se
fait manuellement, lors de l'ouverture de l'application par l'utilisateur
(usage personnel a tres faible frequence). L'automatisation (notification
email, etc.) est une piste future hors scope V1/V2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

#: Chemin local du fichier de stockage des alertes.
CHEMIN_FICHIER_ALERTES = Path(__file__).parent / "data" / "alertes.json"


@dataclass
class Alerte:
    '''Une alerte produit configuree par l'utilisateur.'''

    nom: str
    nom_recherche_associee: str   # Doit correspondre a une RechercheSauvegardee (favoris.py)
    prix_seuil: float | None = None  # Si fourni : alerte declenchee sous ce prix
    date_creation: datetime | None = None
    date_derniere_verification: datetime | None = None


def _charger_fichier() -> dict:
    '''Charge le contenu brut du fichier JSON d'alertes (ou une structure vide si absent).

    TODO (V2): meme logique que favoris._charger_fichier, structure par
    defaut suggeree : {"alertes": []}.
    '''
    raise NotImplementedError("A implementer en V2")


def _sauvegarder_fichier(contenu: dict) -> None:
    '''Ecrit la structure complete dans le fichier JSON d'alertes (ecrasement).

    TODO (V2): json.dump(contenu, ..., ensure_ascii=False, indent=2, default=str
    pour gerer la serialisation des datetime).
    '''
    raise NotImplementedError("A implementer en V2")


def creer_alerte(nom: str, nom_recherche_associee: str, prix_seuil: float | None = None) -> Alerte:
    '''Cree une nouvelle alerte liee a une recherche sauvegardee existante.

    TODO (V2):
    - Verifier que `nom_recherche_associee` existe bien parmi les recherches
      sauvegardees (favoris.lister_recherches_sauvegardees()).
    - Construire l'objet Alerte avec date_creation = datetime.now().
    - Charger le fichier, ajouter l'alerte, sauvegarder, puis la retourner.
    '''
    raise NotImplementedError("A implementer en V2")


def lister_alertes() -> list[Alerte]:
    '''Renvoie la liste de toutes les alertes configurees.

    TODO (V2): charger le fichier et reconstruire une liste d'objets Alerte.
    '''
    raise NotImplementedError("A implementer en V2")


def supprimer_alerte(nom: str) -> None:
    '''Supprime une alerte par son nom.

    TODO (V2): charger, filtrer, sauvegarder.
    '''
    raise NotImplementedError("A implementer en V2")


def verifier_alertes_manuellement() -> list[dict]:
    '''Execute, a la demande de l'utilisateur, la recherche associee a chaque alerte
    et renvoie la liste des alertes declenchees (avec les annonces concernees).

    TODO (V2):
    - Pour chaque Alerte, recharger la RechercheSauvegardee associee
      (favoris.py), relancer la recherche (connecteurs + filtres + scoring),
      et comparer le meilleur prix trouve a `prix_seuil` si defini.
    - Mettre a jour date_derniere_verification pour chaque alerte traitee.
    - Retourner une liste de resultats structures (ex. [{"alerte": ...,
      "annonces_correspondantes": [...]}]) consommable directement par
      l'onglet Favoris / alertes de app.py.
    - Ne pas oublier le delai entre requetes (voir connecteurs/base.py) si
      plusieurs alertes relancent des recherches successives.
    '''
    raise NotImplementedError("A implementer en V2")
