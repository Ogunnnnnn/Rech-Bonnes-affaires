"""
connecteurs/base.py

Definit l'interface commune que doit respecter chaque connecteur de site
de petites annonces (Le Bon Coin, Vinted, et plus tard Facebook Marketplace).

Objectif pedagogique : isoler la logique specifique a chaque site derriere
un contrat unique, afin que le reste de l'application (app.py, scoring.py,
distance.py, ...) puisse manipuler des annonces de n'importe quel site de
maniere identique, sans savoir d'ou elles viennent.

Aucune implementation reseau ici : ce fichier ne contient que les
structures de donnees et la classe abstraite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EtatProduit(str, Enum):
    '''Etats declares possibles pour un produit d'occasion.

    TODO: ajuster cette liste si les sites utilisent des libelles differents
    (ex. Vinted a ses propres categories d'etat) -- prevoir une fonction de
    mapping dans chaque connecteur concret (etat_site -> EtatProduit).
    '''

    NEUF_AVEC_ETIQUETTE = "neuf_avec_etiquette"
    NEUF_SANS_ETIQUETTE = "neuf_sans_etiquette"
    TRES_BON_ETAT = "tres_bon_etat"
    BON_ETAT = "bon_etat"
    SATISFAISANT = "satisfaisant"
    POUR_PIECES = "pour_pieces"
    INCONNU = "inconnu"


@dataclass
class Annonce:
    '''Representation normalisee d'une annonce, commune a tous les sites.

    Chaque connecteur concret (leboncoin.py, vinted.py, ...) est responsable
    de convertir le format brut du site (HTML ou JSON) vers cette structure,
    afin que le reste de l'application n'ait jamais a connaitre les
    particularites d'un site en particulier.
    '''

    id_externe: str                  # Identifiant de l'annonce sur le site d'origine
    site: str                        # Nom du site d'origine, ex. "leboncoin", "vinted"
    titre: str
    prix: float                      # Prix en euros
    url: str                         # Lien vers l'annonce originale
    ville: str | None = None
    code_postal: str | None = None
    latitude: float | None = None    # Renseigne via geocodage.py si absent du site
    longitude: float | None = None
    etat: EtatProduit = EtatProduit.INCONNU
    date_publication: datetime | None = None
    livraison_disponible: bool = False
    nom_vendeur: str | None = None
    score_fiabilite_vendeur: float | None = None  # 0-100, selon donnees disponibles sur le site
    url_photo_principale: str | None = None
    mots_cles_bruts: list[str] = field(default_factory=list)  # Titre/description tokenises

    # TODO (V3 - scoring.py): ajouter un champ `nombre_objets_estime` pour la
    # detection de lots/bundles, rempli par une heuristique sur le titre/la
    # description (ex. "lot de 5", "x3", ...).


class ConnecteurAnnonces(ABC):
    '''Interface commune a tous les connecteurs de sites d'annonces.

    Chaque site concret (LeBonCoinConnecteur, VintedConnecteur, et plus tard
    FacebookMarketplaceConnecteur) doit heriter de cette classe et implementer
    les methodes abstraites ci-dessous. Cela garantit que `app.py` peut
    appeler `connecteur.rechercher(filtres)` de maniere identique, quel que
    soit le site.
    '''

    #: Nom court et stable du site, utilise pour l'affichage et le filtrage
    #: multisite (doit correspondre aux cles utilisees dans filtres.py).
    nom_site: str = "a_definir"

    @abstractmethod
    def rechercher(self, filtres) -> list[Annonce]:
        '''Execute une recherche sur le site et renvoie une liste d'Annonce normalisees.

        Parametres
        ----------
        filtres : filtres.FiltresRecherche
            Objet contenant tous les criteres de recherche (mot-cle, prix,
            etat, villes/rayons, ...). Chaque connecteur n'utilise que les
            criteres qu'il est capable de transmettre nativement au site (ex.
            mot-cle, prix min/max) ; les autres criteres (rayon geographique
            precis, mots-cles exclus, etc.) sont ensuite appliques cote
            application par les modules distance.py et filtres.py.

        Retourne
        --------
        list[Annonce]
            Liste des annonces trouvees, deja converties au format commun.

        TODO (implementation V1):
        - Construire l'URL/les parametres de requete specifiques au site.
        - Effectuer la requete HTTP (avec un User-Agent raisonnable et un
          delai minimal entre deux requetes - voir _attendre_entre_requetes).
        - Parser la reponse (HTML via BeautifulSoup ou JSON interne au site).
        - Convertir chaque resultat brut en objet Annonce via _parser_annonce.
        - Gerer proprement les erreurs reseau/structure sans faire planter
          l'application (retourner une liste vide + logguer l'erreur).
        '''
        raise NotImplementedError

    @abstractmethod
    def _construire_url_recherche(self, filtres) -> str:
        '''Construit l'URL (ou l'endpoint) de recherche propre au site, a partir des filtres.

        TODO: inclure dans l'URL les criteres supportes nativement par le site
        (mot-cle, categorie, prix min/max, localisation si l'API le permet).
        '''
        raise NotImplementedError

    @abstractmethod
    def _parser_annonce(self, donnee_brute) -> Annonce:
        '''Convertit une annonce brute (dict JSON ou element HTML) en objet Annonce.

        TODO: mapper precisement chaque champ du site vers Annonce, et utiliser
        EtatProduit pour normaliser l'etat declare du produit.
        '''
        raise NotImplementedError

    def _attendre_entre_requetes(self, secondes: float = 2.0) -> None:
        '''Introduit un delai entre deux requetes HTTP successives.

        Usage strictement personnel et peu frequent : ce delai limite le risque
        de blocage par le site et respecte un usage raisonnable (pas de
        scraping massif). A appeler explicitement par chaque connecteur concret
        entre deux appels reseau (ex. pagination).

        TODO: implementer avec time.sleep(secondes) dans les connecteurs concrets.
        '''
        raise NotImplementedError
