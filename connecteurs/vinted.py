"""
connecteurs/vinted.py

Connecteur specifique au site Vinted (https://www.vinted.fr), oriente mode/
articles d'occasion (vetements, accessoires, articles enfants, etc.).

Implemente l'interface ConnecteurAnnonces definie dans connecteurs/base.py.

IMPORTANT (limite connue) : comme Le Bon Coin, Vinted ne propose pas d'API
publique officielle. Le site expose neanmoins souvent un endpoint JSON
interne utilise par son propre frontend (observable via les outils de
developpement du navigateur), potentiellement plus simple a parser qu'un
HTML complet, mais tout aussi susceptible de changer sans preavis.
Ce fichier ne contient a ce stade AUCUNE implementation de scraping reelle :
uniquement la structure et les signatures, a completer en V1.
"""

from __future__ import annotations

import time

from .base import Annonce, ConnecteurAnnonces, EtatProduit


class VintedConnecteur(ConnecteurAnnonces):
    '''Connecteur pour Vinted.

    TODO (V1):
    - Identifier l'endpoint JSON interne utilise par le site pour la recherche
      (souvent sous la forme /api/v2/... observable via les outils reseau du
      navigateur) et son format de reponse.
    - Definir un mapping entre les codes d'etat Vinted (ex. "very_good",
      "good", "satisfactory", ...) et EtatProduit.
    - Vinted expose generalement une note/un nombre d'avis par vendeur : s'en
      servir pour alimenter Annonce.score_fiabilite_vendeur.
    - Gerer la pagination (parametre page/cursor selon l'API interne).
    '''

    nom_site = "vinted"

    #: URL de base du site, a utiliser dans _construire_url_recherche.
    URL_BASE = "https://www.vinted.fr"

    #: Delai minimal (en secondes) a respecter entre deux requetes successives,
    #: pour rester dans un usage personnel raisonnable (voir ARCHITECTURE.md).
    DELAI_ENTRE_REQUETES_SEC = 2.0

    def rechercher(self, filtres) -> list[Annonce]:
        '''Recherche des annonces sur Vinted correspondant aux filtres.

        TODO (V1):
        1. Construire l'URL/les parametres de requete via
           self._construire_url_recherche(filtres).
        2. Effectuer la requete HTTP (requests.get) avec les en-tetes adaptes
           (et gestion d'un eventuel jeton de session/cookie si necessaire).
        3. Attendre self.DELAI_ENTRE_REQUETES_SEC avant toute requete suivante
           (pagination) via self._attendre_entre_requetes(...).
        4. Parser la reponse JSON.
        5. Convertir chaque resultat brut en Annonce via self._parser_annonce(...).
        6. Retourner la liste d'Annonce. En cas d'erreur reseau ou de structure
           inattendue (site modifie), logguer l'erreur et retourner [] plutot
           que de lever une exception qui bloquerait toute l'application.
        '''
        raise NotImplementedError("A implementer en V1 : scraping Vinted")

    def _construire_url_recherche(self, filtres) -> str:
        '''Construit l'URL/les parametres de recherche Vinted a partir des filtres.

        TODO: traduire filtres.mot_cle, filtres.prix_min, filtres.prix_max en
        parametres de requete propres a l'endpoint Vinted retenu. Vinted
        n'ayant pas de notion de "ville + rayon" aussi fine que Le Bon Coin
        pour un usage simple, le filtrage geographique precis sera, comme
        pour les autres connecteurs, finalise cote application (distance.py).
        '''
        raise NotImplementedError("A implementer en V1")

    def _parser_annonce(self, donnee_brute) -> Annonce:
        '''Convertit une annonce brute Vinted (dict JSON) en Annonce.

        TODO: extraire titre, prix (attention: Vinted distingue souvent le
        prix article et les frais de port, a clarifier dans Annonce.prix),
        ville si disponible, URL de l'annonce, etat declare (mapping vers
        EtatProduit), date de publication, et note/fiabilite du vendeur.
        '''
        raise NotImplementedError("A implementer en V1")

    def _attendre_entre_requetes(self, secondes: float | None = None) -> None:
        '''Attend un delai raisonnable avant la requete suivante (pagination).'''
        time.sleep(secondes if secondes is not None else self.DELAI_ENTRE_REQUETES_SEC)
