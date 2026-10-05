"""
connecteurs

Package regroupant les connecteurs vers les differents sites de petites
annonces d'occasion (Le Bon Coin, Vinted, et plus tard Facebook
Marketplace, ...).

Il expose :
- les structures de donnees communes a tous les sites (`Annonce`,
  `EtatProduit`) et l'interface abstraite que chaque connecteur concret
  doit respecter (`ConnecteurAnnonces`), definies dans `base.py` ;
- les connecteurs concrets de chaque site : `LeBonCoinConnecteur`
  (leboncoin.py) et `VintedConnecteur` (vinted.py).

Ainsi, le reste de l'application (app.py, scoring.py, distance.py, ...)
peut importer directement depuis `connecteurs` sans se preoccuper du
module exact ou se trouve chaque classe, par exemple :

    from connecteurs import Annonce, LeBonCoinConnecteur, VintedConnecteur
"""

from __future__ import annotations

from .base import Annonce, ConnecteurAnnonces, EtatProduit
from .leboncoin import LeBonCoinConnecteur
from .vinted import VintedConnecteur

__all__ = [
    "Annonce",
    "ConnecteurAnnonces",
    "EtatProduit",
    "LeBonCoinConnecteur",
    "VintedConnecteur",
]
