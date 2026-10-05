"""
connecteurs/leboncoin.py

Connecteur specifique au site Le Bon Coin (https://www.leboncoin.fr).

Implemente l'interface ConnecteurAnnonces definie dans connecteurs/base.py.

IMPORTANT (limite connue) : Le Bon Coin ne propose pas d'API publique
officielle destinee aux developpeurs tiers. Ce connecteur devra s'appuyer
soit sur le parsing du HTML des pages de resultats, soit sur l'appel des
endpoints JSON internes utilises par le site lui-meme (observables via les
outils de developpement du navigateur), qui peuvent changer sans preavis.
Ce fichier ne contient a ce stade AUCUNE implementation de scraping reelle :
uniquement la structure et les signatures, a completer en V1.
"""

from __future__ import annotations

import time

from .base import Annonce, ConnecteurAnnonces, EtatProduit


class LeBonCoinConnecteur(ConnecteurAnnonces):
    '''Connecteur pour Le Bon Coin.

    TODO (V1):
    - Determiner la methode d'acces la plus stable (endpoint JSON interne vs
      HTML public) en inspectant le trafic reseau du site dans un navigateur.
    - Definir un User-Agent realiste et des en-tetes HTTP minimaux.
    - Gerer la pagination (le site limite le nombre d'annonces par page).
    - Prevoir un mapping EtatProduit <-> libelles d'etat utilises par le site.
    '''

    nom_site = "leboncoin"

    #: URL de base du site, a utiliser dans _construire_url_recherche.
    URL_BASE = "https://www.leboncoin.fr"

    #: Delai minimal (en secondes) a respecter entre deux requetes successives,
    #: pour rester dans un usage personnel raisonnable (voir ARCHITECTURE.md).
    DELAI_ENTRE_REQUETES_SEC = 2.0

    def rechercher(self, filtres) -> list[Annonce]:
        '''Recherche des annonces sur Le Bon Coin correspondant aux filtres.

        TODO (V1):
        1. Construire l'URL de recherche via self._construire_url_recherche(filtres).
        2. Effectuer la requete HTTP (requests.get) avec les en-tetes adaptes.
        3. Attendre self.DELAI_ENTRE_REQUETES_SEC avant toute requete suivante
           (pagination) via self._attendre_entre_requetes(...).
        4. Parser la reponse (JSON ou HTML selon la methode retenue).
        5. Convertir chaque resultat brut en Annonce via self._parser_annonce(...).
        6. Retourner la liste d'Annonce. En cas d'erreur reseau ou de structure
           inattendue (site modifie), logguer l'erreur et retourner [] plutot
           que de lever une exception qui bloquerait toute l'application.
        '''
        raise NotImplementedError("A implementer en V1 : scraping Le Bon Coin")

    def _construire_url_recherche(self, filtres) -> str:
        '''Construit l'URL de recherche Le Bon Coin a partir des filtres.

        TODO: traduire filtres.mot_cle, filtres.prix_min, filtres.prix_max
        (et eventuellement une localisation grossiere) en parametres d'URL
        propres au site. Les criteres plus fins (rayon precis, mots-cles
        exclus, seuil fiabilite vendeur) seront appliques cote application
        apres recuperation des resultats bruts (voir distance.py, filtres.py).
        '''
        raise NotImplementedError("A implementer en V1")

    def _parser_annonce(self, donnee_brute) -> Annonce:
        '''Convertit une annonce brute Le Bon Coin (dict JSON ou element HTML) en Annonce.

        TODO: extraire titre, prix, ville/code postal, URL de l'annonce, etat
        declare (via un mapping vers EtatProduit), date de publication,
        disponibilite de la livraison, et si possible un indicateur de
        fiabilite du vendeur (ex. note, nombre d'avis si expose par le site).
        '''
        raise NotImplementedError("A implementer en V1")

    def _attendre_entre_requetes(self, secondes: float | None = None) -> None:
        '''Attend un delai raisonnable avant la requete suivante (pagination).'''
        time.sleep(secondes if secondes is not None else self.DELAI_ENTRE_REQUETES_SEC)
