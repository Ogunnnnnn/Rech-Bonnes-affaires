"""
connecteurs/leboncoin.py

Connecteur specifique au site Le Bon Coin (https://www.leboncoin.fr).

Implemente l'interface ConnecteurAnnonces definie dans connecteurs/base.py.

IMPORTANT (limites connues - a lire avant toute utilisation) :
- Le Bon Coin ne propose AUCUNE API publique officielle destinee aux
  developpeurs tiers. Ce connecteur fonctionne donc par scraping HTML
  "best effort" de la page de resultats publique (requests + BeautifulSoup,
  parser "html.parser" uniquement - PAS lxml, cf. requirements.txt).
- Le Bon Coin peut, a tout moment et sans preavis, modifier la structure de
  ses pages (noms de classes CSS, attributs data-*, rendu cote client via
  JavaScript/React). Si cela se produit, le parsing ci-dessous peut cesser
  de fonctionner partiellement ou totalement : dans ce cas, `rechercher`
  renvoie une liste vide plutot que de planter l'application, et un message
  est journalise (module `logging`) pour faciliter le diagnostic.
- Ce connecteur est prevu pour un usage strictement PERSONNEL et PONCTUEL
  (quelques recherches, pas de scraping massif/automatise en boucle). Un
  delai aleatoire est applique entre deux requetes (voir
  `_attendre_entre_requetes`) afin de limiter le risque de blocage par le
  site et de rester raisonnable dans le volume de requetes envoyees.
- Comme beaucoup de sites modernes, une partie du contenu de Le Bon Coin est
  generee cote client (JavaScript). Il est donc possible que le HTML brut
  recupere via `requests` ne contienne pas (ou que partiellement) les
  annonces visibles dans un vrai navigateur. Ce module tente plusieurs
  selecteurs CSS/attributs connus a titre de "meilleur effort", mais ne
  garantit pas l'exhaustivite des resultats. Pour une solution plus robuste,
  un navigateur headless (ex. Playwright/Selenium) serait necessaire, ce qui
  sort du cadre (option A : requests + BeautifulSoup) demande ici.
"""

from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from .base import Annonce, ConnecteurAnnonces, EtatProduit

# Logger du module : permet de diagnostiquer les erreurs reseau/parsing sans
# jamais faire planter le reste de l'application (app.py).
logger = logging.getLogger(__name__)


class LeBonCoinConnecteur(ConnecteurAnnonces):
    """Connecteur pour Le Bon Coin (scraping HTML, usage personnel et ponctuel).

    Voir le docstring de module ci-dessus pour les limites importantes
    (absence d'API officielle, fragilite du parsing HTML, contenu genere en
    JavaScript cote client).
    """

    nom_site = "leboncoin"

    #: URL de base du site, utilisee dans _construire_url_recherche.
    URL_BASE = "https://www.leboncoin.fr"

    #: URL du moteur de recherche public (page de resultats classiques).
    URL_RECHERCHE = "https://www.leboncoin.fr/recherche"

    #: Delai minimal (en secondes) a respecter entre deux requetes successives,
    #: pour rester dans un usage personnel raisonnable (voir ARCHITECTURE.md).
    DELAI_ENTRE_REQUETES_SEC = 2.0

    #: Bornes du delai aleatoire applique entre deux requetes (anti-blocage).
    DELAI_MIN_SEC = 2.0
    DELAI_MAX_SEC = 4.0

    #: User-Agent "realiste" de navigateur recent, pour limiter le risque
    #: d'etre immediatement rejete par des protections anti-bot basiques.
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    #: Delai (en secondes) applique a la requete HTTP avant d'abandonner.
    TIMEOUT_SEC = 10

    #: Mapping (best effort) des libelles d'etat tels qu'affiches par Le Bon
    #: Coin vers l'enum EtatProduit commune a l'application. A ajuster si le
    #: site utilise d'autres libelles.
    MAPPING_ETAT = {
        "neuf avec étiquette": EtatProduit.NEUF_AVEC_ETIQUETTE,
        "neuf": EtatProduit.NEUF_SANS_ETIQUETTE,
        "neuf sans étiquette": EtatProduit.NEUF_SANS_ETIQUETTE,
        "très bon état": EtatProduit.TRES_BON_ETAT,
        "tres bon etat": EtatProduit.TRES_BON_ETAT,
        "bon état": EtatProduit.BON_ETAT,
        "bon etat": EtatProduit.BON_ETAT,
        "satisfaisant": EtatProduit.SATISFAISANT,
        "état satisfaisant": EtatProduit.SATISFAISANT,
        "pour pièces": EtatProduit.POUR_PIECES,
        "pour pieces": EtatProduit.POUR_PIECES,
    }

    # ------------------------------------------------------------------
    # Methode principale (point d'entree utilise par app.py)
    # ------------------------------------------------------------------
    def rechercher(self, filtres) -> list[Annonce]:
        """Recherche des annonces sur Le Bon Coin correspondant aux filtres.

        Cette methode ne leve jamais d'exception vers l'appelant : toute
        erreur reseau ou de parsing est journalisee et une liste vide est
        renvoyee, afin que le reste de l'application (recherche multisite)
        continue de fonctionner meme si Le Bon Coin est indisponible ou a
        change de structure HTML.
        """
        annonces: list[Annonce] = []

        # 1. Construction de l'URL de recherche a partir des filtres.
        try:
            url = self._construire_url_recherche(filtres)
        except Exception:
            logger.exception("LeBonCoin : impossible de construire l'URL de recherche.")
            return []

        # 2. Requete HTTP avec en-tetes realistes de navigateur.
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }

        reponse = None
        try:
            reponse = requests.get(url, headers=headers, timeout=self.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            logger.warning("LeBonCoin : la requete a expire (timeout) pour %s", url)
            return []
        except requests.exceptions.RequestException:
            # Regroupe toutes les erreurs reseau (connexion refusee, DNS, SSL, ...).
            logger.exception("LeBonCoin : erreur reseau lors de la requete vers %s", url)
            return []
        finally:
            # On respecte le delai anti-blocage, qu'il y ait eu succes ou echec,
            # avant toute eventuelle requete suivante (ex. pagination future).
            self._attendre_entre_requetes()

        # 3. Verification du code de statut HTTP.
        if reponse is None or reponse.status_code != 200:
            code = reponse.status_code if reponse is not None else "inconnu"
            logger.warning("LeBonCoin : code HTTP non-200 recu (%s) pour %s", code, url)
            return []

        # 4. Parsing du HTML avec BeautifulSoup (parser natif "html.parser").
        try:
            soupe = BeautifulSoup(reponse.text, "html.parser")
        except Exception:
            logger.exception("LeBonCoin : echec du parsing HTML de la page de resultats.")
            return []

        # 5. Extraction des blocs d'annonces bruts (plusieurs selecteurs
        # essayes successivement car la structure du site peut varier).
        try:
            blocs_annonces = self._extraire_blocs_annonces(soupe)
        except Exception:
            logger.exception("LeBonCoin : echec de l'extraction des blocs d'annonces.")
            return []

        if not blocs_annonces:
            logger.info(
                "LeBonCoin : aucune annonce trouvee dans le HTML recu (page "
                "possiblement generee en JavaScript, ou structure modifiee)."
            )
            return []

        # 6. Conversion de chaque bloc brut en objet Annonce normalise.
        for bloc in blocs_annonces:
            try:
                annonce = self._parser_annonce(bloc)
            except Exception:
                # Une annonce individuelle mal formee ne doit pas faire
                # echouer toute la recherche : on la saute simplement.
                logger.exception("LeBonCoin : echec du parsing d'une annonce, elle est ignoree.")
                continue
            if annonce is not None:
                annonces.append(annonce)

        return annonces

    # ------------------------------------------------------------------
    # Construction de l'URL de recherche
    # ------------------------------------------------------------------
    def _construire_url_recherche(self, filtres) -> str:
        """Construit l'URL de recherche Le Bon Coin a partir des filtres.

        Traduit filtres.mot_cle, filtres.prix_min, filtres.prix_max et une
        eventuelle localisation (premiere entree de filtres.villes_rayons) en
        parametres de requete (query string) proches de ceux utilises par le
        moteur de recherche public de Le Bon Coin. Les criteres plus fins
        (rayon precis multi-villes, mots-cles exclus, seuil de fiabilite
        vendeur, ...) sont appliques cote application apres recuperation des
        resultats bruts (voir distance.py / filtres.py), pas ici.
        """
        parametres: dict[str, str] = {}

        # Mot-cle de recherche (texte libre).
        mot_cle = getattr(filtres, "mot_cle", "") or ""
        if mot_cle.strip():
            parametres["text"] = mot_cle.strip()

        # Prix min/max : Le Bon Coin attend un parametre "price" au format
        # "min-max" (bornes optionnelles de part et d'autre du tiret).
        prix_min = getattr(filtres, "prix_min", None)
        prix_max = getattr(filtres, "prix_max", None)
        if prix_min is not None or prix_max is not None:
            borne_min = str(int(prix_min)) if prix_min is not None else ""
            borne_max = str(int(prix_max)) if prix_max is not None else ""
            parametres["price"] = f"{borne_min}-{borne_max}"

        # Localisation grossiere : on ne transmet que la premiere zone de
        # recherche (ville/code postal) a titre indicatif ; le filtrage fin
        # par rayon reel est fait ensuite cote application (distance.py).
        villes_rayons = getattr(filtres, "villes_rayons", None) or []
        if villes_rayons:
            premiere_zone = villes_rayons[0]
            ville = getattr(premiere_zone, "ville_ou_code_postal", None)
            if ville:
                parametres["locations"] = str(ville).strip()

        # Construction finale de l'URL avec encodage correct des parametres.
        if parametres:
            return f"{self.URL_RECHERCHE}?{urlencode(parametres)}"
        return self.URL_RECHERCHE

    # ------------------------------------------------------------------
    # Extraction des blocs HTML d'annonces (etape interne a rechercher)
    # ------------------------------------------------------------------
    def _extraire_blocs_annonces(self, soupe: BeautifulSoup) -> list:
        """Essaie plusieurs selecteurs connus pour retrouver les cartes d'annonces.

        La structure HTML de Le Bon Coin ayant deja change plusieurs fois par
        le passe, on tente successivement differents attributs/classes
        "historiquement" utilises par le site, et on retient le premier
        selecteur qui renvoie au moins un resultat.
        """
        selecteurs_possibles = [
            {"name": "a", "attrs": {"data-qa-id": "aditem_container"}},
            {"name": "a", "attrs": {"data-test-id": "ad"}},
            {"name": "div", "attrs": {"data-qa-id": "aditem_container"}},
        ]

        for selecteur in selecteurs_possibles:
            resultats = soupe.find_all(selecteur["name"], attrs=selecteur["attrs"])
            if resultats:
                return resultats

        # Dernier recours : recherche par motif de classe CSS (les classes
        # generees automatiquement contiennent souvent "aditem" ou "adCard").
        resultats = soupe.find_all(attrs={"class": re.compile(r"(aditem|adCard|ListItem)", re.IGNORECASE)})
        return resultats

    # ------------------------------------------------------------------
    # Conversion d'une annonce brute en objet Annonce normalise
    # ------------------------------------------------------------------
    def _parser_annonce(self, donnee_brute) -> Annonce:
        """Convertit une annonce brute Le Bon Coin (tag BeautifulSoup ou dict) en Annonce.

        Gere les deux formats bruts possibles :
        - un `bs4.Tag` issu du parsing HTML de la page de resultats ;
        - un `dict` (ex. pour des tests unitaires, ou si une future version
          utilise un endpoint JSON interne).
        Tous les champs manquants ou mal formes recoivent une valeur par
        defaut sensee plutot que de lever une exception.
        """
        if isinstance(donnee_brute, dict):
            return self._parser_annonce_depuis_dict(donnee_brute)
        return self._parser_annonce_depuis_tag(donnee_brute)

    def _parser_annonce_depuis_tag(self, tag) -> Annonce:
        """Extrait les champs d'une annonce a partir d'un tag HTML BeautifulSoup."""

        # --- URL de l'annonce ---
        url = ""
        try:
            href = tag.get("href") if hasattr(tag, "get") else None
            if href:
                url = href if href.startswith("http") else f"{self.URL_BASE}{href}"
        except Exception:
            url = ""

        # --- Identifiant externe : extrait de l'URL (dernier segment numerique) ---
        id_externe = ""
        try:
            correspondance = re.search(r"/(\d+)(?:\.htm)?(?:\?.*)?$", url)
            id_externe = correspondance.group(1) if correspondance else ""
        except Exception:
            id_externe = ""
        if not id_externe:
            # A defaut d'identifiant propre, on retombe sur l'URL complete
            # (mieux qu'une chaine vide pour la deduplication en aval).
            id_externe = url or "inconnu"

        # --- Titre ---
        titre = "Titre indisponible"
        try:
            titre_tag = tag.find(attrs={"data-qa-id": "aditem_title"}) if hasattr(tag, "find") else None
            if titre_tag is None and hasattr(tag, "find"):
                titre_tag = tag.find("p") or tag.find("h2") or tag.find("h3")
            if titre_tag is not None:
                texte = titre_tag.get_text(strip=True)
                if texte:
                    titre = texte
        except Exception:
            pass

        # --- Prix ---
        prix = 0.0
        try:
            prix_tag = tag.find(attrs={"data-qa-id": "aditem_price"}) if hasattr(tag, "find") else None
            texte_prix = prix_tag.get_text(strip=True) if prix_tag is not None else ""
            if not texte_prix and hasattr(tag, "get_text"):
                # Repli : recherche d'un motif "123 €" dans tout le bloc.
                correspondance_prix = re.search(r"(\d[\d\s]*)\s?€", tag.get_text(" ", strip=True))
                texte_prix = correspondance_prix.group(1) if correspondance_prix else ""
            texte_prix_nettoye = re.sub(r"[^\d]", "", texte_prix)
            if texte_prix_nettoye:
                prix = float(texte_prix_nettoye)
        except Exception:
            prix = 0.0

        # --- Ville ---
        ville = None
        try:
            ville_tag = tag.find(attrs={"data-qa-id": "aditem_location"}) if hasattr(tag, "find") else None
            if ville_tag is not None:
                texte_ville = ville_tag.get_text(strip=True)
                # Le libelle de localisation inclut parfois le code postal,
                # ex. "Lyon 69000" : on tente de les separer proprement.
                ville = texte_ville or None
        except Exception:
            ville = None

        # --- Code postal (extrait depuis le texte de ville si present) ---
        code_postal = None
        try:
            if ville:
                correspondance_cp = re.search(r"\b(\d{5})\b", ville)
                if correspondance_cp:
                    code_postal = correspondance_cp.group(1)
                    ville = ville.replace(code_postal, "").strip(" ,-") or None
        except Exception:
            code_postal = None

        # --- Etat du produit (rarement visible directement sur la vignette
        # de resultats ; mapping best effort si un libelle est trouve) ---
        etat = EtatProduit.INCONNU
        try:
            texte_complet = tag.get_text(" ", strip=True).lower() if hasattr(tag, "get_text") else ""
            for libelle, valeur_enum in self.MAPPING_ETAT.items():
                if libelle in texte_complet:
                    etat = valeur_enum
                    break
        except Exception:
            etat = EtatProduit.INCONNU

        # --- Photo principale ---
        url_photo = None
        try:
            img_tag = tag.find("img") if hasattr(tag, "find") else None
            if img_tag is not None:
                url_photo = img_tag.get("src") or img_tag.get("data-src")
        except Exception:
            url_photo = None

        # --- Mots-cles bruts (tokenisation simple du titre) ---
        mots_cles_bruts: list[str] = []
        try:
            mots_cles_bruts = [mot for mot in re.split(r"\W+", titre.lower()) if mot]
        except Exception:
            mots_cles_bruts = []

        return Annonce(
            id_externe=id_externe,
            site=self.nom_site,
            titre=titre,
            prix=prix,
            url=url or self.URL_BASE,
            ville=ville,
            code_postal=code_postal,
            latitude=None,
            longitude=None,
            etat=etat,
            date_publication=None,  # Non fiable sans acces a la page detail de l'annonce.
            livraison_disponible=False,  # Information rarement visible sur la vignette liste.
            nom_vendeur=None,
            score_fiabilite_vendeur=None,
            url_photo_principale=url_photo,
            mots_cles_bruts=mots_cles_bruts,
        )

    def _parser_annonce_depuis_dict(self, donnee: dict) -> Annonce:
        """Extrait les champs d'une annonce a partir d'un dict (ex. donnees de test)."""

        titre = str(donnee.get("titre") or donnee.get("subject") or "Titre indisponible")

        try:
            prix = float(donnee.get("prix", donnee.get("price", 0.0)) or 0.0)
        except (TypeError, ValueError):
            prix = 0.0

        url = str(donnee.get("url") or donnee.get("link") or self.URL_BASE)

        id_externe = str(donnee.get("id_externe") or donnee.get("id") or url)

        ville = donnee.get("ville") or donnee.get("city")
        code_postal = donnee.get("code_postal") or donnee.get("zipcode")

        etat_brut = str(donnee.get("etat") or "").strip().lower()
        etat = self.MAPPING_ETAT.get(etat_brut, EtatProduit.INCONNU)

        date_publication = None
        valeur_date = donnee.get("date_publication") or donnee.get("date")
        if valeur_date:
            try:
                date_publication = datetime.fromisoformat(str(valeur_date))
            except (ValueError, TypeError):
                date_publication = None

        try:
            mots_cles_bruts = [mot for mot in re.split(r"\W+", titre.lower()) if mot]
        except Exception:
            mots_cles_bruts = []

        return Annonce(
            id_externe=id_externe,
            site=self.nom_site,
            titre=titre,
            prix=prix,
            url=url,
            ville=str(ville) if ville else None,
            code_postal=str(code_postal) if code_postal else None,
            latitude=donnee.get("latitude"),
            longitude=donnee.get("longitude"),
            etat=etat,
            date_publication=date_publication,
            livraison_disponible=bool(donnee.get("livraison_disponible", False)),
            nom_vendeur=donnee.get("nom_vendeur"),
            score_fiabilite_vendeur=donnee.get("score_fiabilite_vendeur"),
            url_photo_principale=donnee.get("url_photo_principale") or donnee.get("image"),
            mots_cles_bruts=mots_cles_bruts,
        )

    # ------------------------------------------------------------------
    # Delai anti-blocage entre deux requetes
    # ------------------------------------------------------------------
    def _attendre_entre_requetes(self, secondes: float | None = None) -> None:
        """Attend un delai raisonnable avant la requete suivante (pagination).

        Si `secondes` n'est pas fourni, un delai ALEATOIRE est tire entre
        DELAI_MIN_SEC et DELAI_MAX_SEC (par defaut 2 a 4 secondes), afin de
        limiter le risque d'etre detecte/bloque comme un robot (un delai
        parfaitement constant est plus facilement identifiable qu'un delai
        variable).
        """
        if secondes is not None:
            time.sleep(secondes)
        else:
            time.sleep(random.uniform(self.DELAI_MIN_SEC, self.DELAI_MAX_SEC))
