"""
distance.py

Calcul de distances geographiques entre une annonce (coordonnees GPS) et une
ou plusieurs zones choisies par l'utilisateur (couples ville + rayon en km).

Formule utilisee : Haversine, qui calcule la distance a vol d'oiseau entre
deux points GPS en tenant compte de la courbure de la Terre (suffisamment
precise pour un usage de filtrage d'annonces a l'echelle d'un pays).
"""

from __future__ import annotations

import math

#: Rayon moyen de la Terre en kilometres, utilise par la formule de Haversine.
RAYON_TERRE_KM = 6371.0


def distance_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    '''Calcule la distance en kilometres entre deux points GPS (formule de Haversine).

    Parametres
    ----------
    lat1, lon1 : float
        Latitude/longitude du premier point (degres decimaux).
    lat2, lon2 : float
        Latitude/longitude du second point (degres decimaux).

    Retourne
    --------
    float
        Distance en kilometres entre les deux points.

    TODO (V1): implementer la formule standard de Haversine :
        phi1, phi2 = radians(lat1), radians(lat2)
        delta_phi = radians(lat2 - lat1)
        delta_lambda = radians(lon2 - lon1)
        a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return RAYON_TERRE_KM * c
    '''
    raise NotImplementedError("A implementer en V1")


def annonce_dans_perimetre(annonce, villes_rayons) -> bool:
    '''Indique si une annonce se trouve dans au moins un des perimetres choisis.

    Parametres
    ----------
    annonce : connecteurs.base.Annonce
        Annonce dont on connait (ou a defaut, dont on a geocode) la latitude
        et la longitude.
    villes_rayons : list[filtres.VilleRayon]
        Liste des couples (coordonnees de la ville, rayon_km) choisis par
        l'utilisateur dans le formulaire de recherche.

    Retourne
    --------
    bool
        True si l'annonce est a une distance <= rayon_km d'au moins une des
        villes de la liste, False sinon (ou si les coordonnees de l'annonce
        sont inconnues).

    TODO (V1):
    - Si annonce.latitude/longitude est None, retourner False (impossible de
      conclure ; l'annonce finira dans l'onglet "Autres" si elle propose la
      livraison, sinon elle est simplement ecartee).
    - Sinon, pour chaque ville_rayon, calculer distance_haversine(annonce.lat,
      annonce.lon, ville_rayon.latitude, ville_rayon.longitude) et comparer au
      rayon_km choisi.
    '''
    raise NotImplementedError("A implementer en V1")


def distance_minimale(annonce, villes_rayons) -> float | None:
    '''Renvoie la distance la plus courte entre l'annonce et l'une des villes choisies.

    Utile pour (a) trier les resultats par proximite et (b) alimenter
    l'onglet "Autres" (annonces hors rayon mais potentiellement livrables)
    en indiquant a quelle distance elles se trouvent reellement.

    Retourne None si les coordonnees de l'annonce sont inconnues ou si
    `villes_rayons` est vide.

    TODO (V1): calculer distance_haversine pour chaque ville_rayon et
    retourner le minimum.
    '''
    raise NotImplementedError("A implementer en V1")
