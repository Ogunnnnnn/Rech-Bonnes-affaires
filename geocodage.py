"""
geocodage.py

Conversion d'une saisie utilisateur (nom de ville ou code postal) en
coordonnees GPS (latitude, longitude), necessaires au calcul de distance
(distance.py) pour le filtrage geographique multi-villes avec rayon.

Source de donnees retenue : le referentiel public des communes francaises
disponible sur data.gouv.fr (ou l'API Geo officielle qui s'appuie sur les
memes donnees), contenant pour chaque commune : nom, code(s) postal(aux),
code INSEE, latitude, longitude, population (approximee ici par le nombre
d'adresses "address_count").

Version V1 : implementation complete et fonctionnelle (plus aucun
NotImplementedError). Le referentiel est charge une seule fois en memoire
(cache module-level paresseux) puis indexe pour permettre des recherches
rapides par nom de commune normalise et par code postal.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

#: Chemin local du cache du referentiel des communes francaises.
#: Le fichier est fourni avec l'application dans le dossier "data/" ;
#: si on souhaite un jour l'actualiser automatiquement, voir
#: `telecharger_cache_communes_si_absent`.
CHEMIN_CACHE_COMMUNES = Path(__file__).parent / "data" / "communes_france.csv"

#: URL source possible pour le telechargement initial (a verifier/ajuster au
#: moment de l'implementation, l'URL exacte du jeu de donnees peut evoluer).
URL_COMMUNES_DATA_GOUV = "https://www.data.gouv.fr/fr/datasets/communes-de-france/"

#: Colonnes attendues dans le CSV (sert a detecter un fichier corrompu /
#: incompatible le plus tot possible, avec un message clair).
COLONNES_REQUISES = {
    "commune_insee_code",
    "commune_name",
    "postal_code",
    "latitude",
    "longitude",
    "address_count",
}


class CommuneIntrouvable(Exception):
    """Levee quand aucune commune ne correspond a la recherche effectuee.

    Utilisee pour une recherche par nom de commune ou par code postal qui
    n'aboutit a aucun resultat, y compris apres recherche approximative.
    """


class ReferentielCommunesInvalide(Exception):
    """Levee quand le fichier CSV des communes est absent, vide ou mal forme."""


@dataclass
class Coordonnees:
    """Coordonnees GPS d'une commune, avec quelques metadonnees utiles."""

    nom_commune: str
    code_postal: str
    code_insee: str
    latitude: float
    longitude: float


# ---------------------------------------------------------------------------
# Cache memoire module-level (paresseux) : on ne charge/indexe le CSV
# qu'une seule fois par processus, quel que soit le nombre d'appels aux
# fonctions de recherche ci-dessous.
# ---------------------------------------------------------------------------
_CACHE: dict = {
    "chemin": None,          # Path utilise pour construire le cache courant
    "communes": None,        # list[Coordonnees] : toutes les lignes du CSV
    "index_nom": None,       # dict[str, list[tuple[Coordonnees, int]]] : nom normalise -> (coord, address_count)
    "index_code_postal": None,  # dict[str, list[tuple[Coordonnees, int]]] : code postal -> (coord, address_count)
}


def telecharger_cache_communes_si_absent(chemin: Path = CHEMIN_CACHE_COMMUNES) -> None:
    """Telecharge le referentiel des communes depuis data.gouv.fr si absent localement.

    En pratique, le fichier "communes_france.csv" est distribue avec
    l'application dans le dossier "data/" : cette fonction ne fait donc
    rien si le fichier est deja present (cas attendu en production).

    Si le fichier est absent, on tente un telechargement reseau (via la
    librairie `requests`, importee ici seulement pour ne pas l'exiger si
    elle n'est pas necessaire). En cas d'echec (pas de reseau, dependance
    absente, URL perimee...), on leve une erreur explicite afin que
    l'utilisateur sache qu'il doit fournir le fichier CSV manuellement.
    """
    chemin = Path(chemin)
    if chemin.exists():
        # Cache local deja present : rien a faire.
        return

    chemin.parent.mkdir(parents=True, exist_ok=True)

    try:
        import requests  # import local : optionnel, uniquement utile ici
    except ImportError as exc:
        raise ReferentielCommunesInvalide(
            f"Le fichier '{chemin}' est absent et la librairie 'requests' "
            "n'est pas installee pour le telecharger automatiquement. "
            "Merci de placer manuellement 'communes_france.csv' dans le "
            f"dossier '{chemin.parent}'."
        ) from exc

    try:
        reponse = requests.get(URL_COMMUNES_DATA_GOUV, timeout=30)
        reponse.raise_for_status()
        chemin.write_bytes(reponse.content)
    except Exception as exc:  # noqa: BLE001 - on veut un message clair, peu importe la cause
        raise ReferentielCommunesInvalide(
            f"Impossible de telecharger automatiquement le referentiel des "
            f"communes depuis '{URL_COMMUNES_DATA_GOUV}' ({exc}). "
            "Merci de fournir manuellement le fichier 'communes_france.csv' "
            f"dans le dossier '{chemin.parent}'."
        ) from exc


def _normaliser_texte(texte: str) -> str:
    """Normalise un texte pour la recherche (minuscules, sans accents, trim).

    - Retire les accents (NFKD puis suppression des caracteres diacritiques).
    - Remplace tirets, apostrophes et ponctuation par des espaces, pour que
      "L'Abergement-Clementiat" et "l abergement clementiat" soient
      equivalents.
    - Met en minuscules et compacte les espaces multiples.
    """
    if texte is None:
        return ""

    texte = str(texte).strip()
    # Decomposition unicode puis suppression des diacritiques (accents).
    texte_sans_accents = unicodedata.normalize("NFKD", texte)
    texte_sans_accents = "".join(
        caractere for caractere in texte_sans_accents if not unicodedata.combining(caractere)
    )
    texte_normalise = texte_sans_accents.lower()
    # Tirets, apostrophes (droites ou typographiques) -> espace.
    texte_normalise = re.sub(r"[-'\u2019]", " ", texte_normalise)
    # Toute autre ponctuation non alphanumerique -> espace.
    texte_normalise = re.sub(r"[^a-z0-9\s]", " ", texte_normalise)
    # Compactage des espaces multiples + trim.
    texte_normalise = re.sub(r"\s+", " ", texte_normalise).strip()
    return texte_normalise


def _normaliser_code_postal(code_postal: str) -> str:
    """Normalise un code postal saisi en chaine de 5 chiffres (zero-pad a gauche).

    Accepte un code postal donne comme entier ou chaine, eventuellement
    avec des espaces (ex. "01 400"), et le ramene a un format uniforme sur
    5 caracteres (ex. "01400"). Leve ValueError si la saisie ne ressemble
    pas a un code postal francais valide.
    """
    code_nettoye = re.sub(r"\s+", "", str(code_postal).strip())
    if not code_nettoye.isdigit():
        raise ValueError(f"'{code_postal}' ne ressemble pas a un code postal valide.")
    if len(code_nettoye) > 5:
        raise ValueError(f"'{code_postal}' ne ressemble pas a un code postal valide.")
    return code_nettoye.zfill(5)


def _lire_lignes_csv(chemin: Path) -> list[dict]:
    """Lit le CSV du referentiel des communes et retourne la liste des lignes (dict).

    Utilise le module standard `csv` (pas pandas) afin de garder ce module
    leger en dependances et peu couteux en memoire (le fichier ne contient
    qu'environ 35 000 lignes, ce qui reste trivial pour une simple liste de
    dicts).
    """
    if not chemin.exists():
        raise ReferentielCommunesInvalide(
            f"Le fichier du referentiel des communes est introuvable : '{chemin}'. "
            "Verifiez qu'il a bien ete place dans le dossier 'data/' de l'application."
        )

    try:
        with open(chemin, newline="", encoding="utf-8") as fichier_csv:
            lecteur = csv.DictReader(fichier_csv)
            if lecteur.fieldnames is None:
                raise ReferentielCommunesInvalide(f"Le fichier '{chemin}' est vide.")

            colonnes_manquantes = COLONNES_REQUISES - set(lecteur.fieldnames)
            if colonnes_manquantes:
                raise ReferentielCommunesInvalide(
                    f"Le fichier '{chemin}' ne contient pas les colonnes attendues : "
                    f"{sorted(colonnes_manquantes)}."
                )

            lignes = list(lecteur)
    except (OSError, UnicodeDecodeError) as exc:
        raise ReferentielCommunesInvalide(
            f"Impossible de lire le fichier '{chemin}' : {exc}"
        ) from exc

    if not lignes:
        raise ReferentielCommunesInvalide(f"Le fichier '{chemin}' ne contient aucune donnee.")

    return lignes


def charger_referentiel_communes(chemin: Path = CHEMIN_CACHE_COMMUNES) -> list[Coordonnees]:
    """Charge en memoire le referentiel des communes depuis le cache local CSV.

    Le chargement et l'indexation (par nom normalise et par code postal) ne
    sont effectues qu'une seule fois par processus : les appels suivants
    avec le meme `chemin` reutilisent le cache memoire module-level
    (`_CACHE`), ce qui est largement suffisant pour un usage personnel a
    faible frequence (pas besoin de base de donnees indexee sur disque).

    Retourne la liste complete des `Coordonnees` (une entree par ligne du
    CSV, une commune pouvant apparaitre plusieurs fois si elle a plusieurs
    codes postaux).
    """
    chemin = Path(chemin)

    if _CACHE["communes"] is not None and _CACHE["chemin"] == chemin:
        # Deja charge pour ce chemin : on reutilise le cache memoire.
        return _CACHE["communes"]

    telecharger_cache_communes_si_absent(chemin)
    lignes = _lire_lignes_csv(chemin)

    communes: list[Coordonnees] = []
    index_nom: dict[str, list[tuple[Coordonnees, int]]] = {}
    index_code_postal: dict[str, list[tuple[Coordonnees, int]]] = {}

    for ligne in lignes:
        try:
            latitude = float(ligne["latitude"])
            longitude = float(ligne["longitude"])
        except (TypeError, ValueError):
            # Ligne sans coordonnees exploitables : on l'ignore plutot que
            # de planter tout le chargement pour une seule ligne corrompue.
            continue

        nom_commune = (ligne.get("commune_name") or "").strip()
        if not nom_commune:
            continue

        try:
            code_postal = _normaliser_code_postal(ligne.get("postal_code", ""))
        except ValueError:
            continue

        code_insee = (ligne.get("commune_insee_code") or "").strip()

        try:
            poids = int(float(ligne.get("address_count") or 0))
        except (TypeError, ValueError):
            poids = 0

        coord = Coordonnees(
            nom_commune=nom_commune,
            code_postal=code_postal,
            code_insee=code_insee,
            latitude=latitude,
            longitude=longitude,
        )
        communes.append(coord)

        nom_norm = _normaliser_texte(nom_commune)
        index_nom.setdefault(nom_norm, []).append((coord, poids))
        index_code_postal.setdefault(code_postal, []).append((coord, poids))

    if not communes:
        raise ReferentielCommunesInvalide(
            f"Aucune commune exploitable n'a pu etre chargee depuis '{chemin}'."
        )

    _CACHE["chemin"] = chemin
    _CACHE["communes"] = communes
    _CACHE["index_nom"] = index_nom
    _CACHE["index_code_postal"] = index_code_postal

    return communes


def _index_nom(chemin: Path = CHEMIN_CACHE_COMMUNES) -> dict[str, list[tuple[Coordonnees, int]]]:
    """Retourne l'index (nom normalise -> communes) en s'assurant que le cache est charge."""
    charger_referentiel_communes(chemin)
    return _CACHE["index_nom"]


def _index_code_postal(chemin: Path = CHEMIN_CACHE_COMMUNES) -> dict[str, list[tuple[Coordonnees, int]]]:
    """Retourne l'index (code postal -> communes) en s'assurant que le cache est charge."""
    charger_referentiel_communes(chemin)
    return _CACHE["index_code_postal"]


def _meilleure_commune(candidats: list[tuple[Coordonnees, int]]) -> Coordonnees:
    """Choisit la commune la plus representative parmi des candidats homonymes.

    En cas d'homonymie (plusieurs communes de meme nom dans des
    departements differents, ou une meme commune avec plusieurs codes
    postaux), on retient par defaut celle avec le plus d'adresses connues
    (`address_count`), utilise ici comme approximation du poids/importance
    de la commune.
    """
    return max(candidats, key=lambda item: item[1])[0]


def geocoder_par_nom(nom_commune: str, chemin: Path = CHEMIN_CACHE_COMMUNES) -> Coordonnees:
    """Geocode une commune a partir de son nom (recherche robuste aux accents/majuscules).

    Strategie :
    1. Normalisation du nom saisi (minuscules, sans accents, sans tirets).
    2. Recherche exacte dans l'index des noms normalises.
    3. A defaut, recherche partielle : toute commune dont le nom normalise
       contient la saisie (ou l'inverse), par exemple "lyon" -> "lyon 2e
       arrondissement".
    4. A defaut, recherche de la correspondance la plus proche (distance
       d'edition) parmi tous les noms connus, via `difflib`.

    En cas d'homonymie, retourne par defaut la commune la plus "importante"
    (cf. `_meilleure_commune`).

    Leve `CommuneIntrouvable` si rien ne correspond, meme approximativement.
    Leve `ValueError` si `nom_commune` est vide ou ne contient que des espaces.
    """
    if nom_commune is None or not str(nom_commune).strip():
        raise ValueError("Le nom de commune ne peut pas etre vide.")

    index = _index_nom(chemin)
    nom_norm = _normaliser_texte(nom_commune)

    # 1) Correspondance exacte (apres normalisation).
    if nom_norm in index:
        return _meilleure_commune(index[nom_norm])

    # 2) Correspondance partielle, sur des limites de mots (pas une simple
    #    sous-chaine brute, pour eviter les faux positifs comme "Ville"
    #    trouve dans "Ville Qui N'Existe Pas Du Tout").
    #    - La saisie est acceptee comme abreviation d'un nom complet connu
    #      (ex. "Lyon" -> "Lyon 3e Arrondissement") sans contrainte de
    #      longueur : l'utilisateur tape volontairement un nom partiel.
    #    - Un nom connu plus court n'est accepte comme correspondance a
    #      l'interieur d'une saisie plus longue que s'il en couvre une part
    #      substantielle (>= 60% des caracteres), afin d'eviter qu'un mot
    #      generique isole (ex. "ville") ne matche n'importe quel texte.
    candidats_partiels: list[tuple[Coordonnees, int]] = []
    for nom_connu, candidats in index.items():
        requete_dans_connu = re.search(rf"\b{re.escape(nom_norm)}\b", nom_connu) is not None
        connu_dans_requete = (
            re.search(rf"\b{re.escape(nom_connu)}\b", nom_norm) is not None
            and len(nom_connu) >= 0.6 * len(nom_norm)
        )
        if requete_dans_connu or connu_dans_requete:
            candidats_partiels.extend(candidats)
    if candidats_partiels:
        return _meilleure_commune(candidats_partiels)

    # 3) Correspondance approximative (la plus proche orthographiquement).
    import difflib

    noms_proches = difflib.get_close_matches(nom_norm, index.keys(), n=1, cutoff=0.75)
    if noms_proches:
        return _meilleure_commune(index[noms_proches[0]])

    raise CommuneIntrouvable(
        f"Aucune commune ne correspond a '{nom_commune}' (meme apres recherche approximative)."
    )


def obtenir_toutes_coordonnees_code_postal(
    code_postal: str, chemin: Path = CHEMIN_CACHE_COMMUNES
) -> list[Coordonnees]:
    """Retourne toutes les communes partageant exactement ce code postal.

    Leve `CommuneIntrouvable` si aucune commune ne correspond.
    Leve `ValueError` si `code_postal` n'a pas un format valide.
    """
    index = _index_code_postal(chemin)
    code_norm = _normaliser_code_postal(code_postal)

    candidats = index.get(code_norm)
    if not candidats:
        raise CommuneIntrouvable(f"Aucune commune ne correspond au code postal '{code_postal}'.")

    # Tri par importance decroissante (plus d'adresses = plus "principal").
    candidats_tries = sorted(candidats, key=lambda item: item[1], reverse=True)
    return [coord for coord, _poids in candidats_tries]


def geocoder_par_code_postal(
    code_postal: str, strategie: str = "premiere", chemin: Path = CHEMIN_CACHE_COMMUNES
) -> Coordonnees:
    """Geocode un code postal, en gerant le cas de plusieurs communes partageant ce code.

    Parametres
    ----------
    code_postal : str
        Code postal francais (4 ou 5 chiffres, ex. "1400" ou "01400").
    strategie : str
        - "premiere" (par defaut) : retourne la commune la plus "importante"
          (la plus grande valeur de `address_count`) parmi celles partageant
          ce code postal.
        - "moyenne" : si plusieurs communes partagent le code postal,
          retourne un point moyen (latitude/longitude moyennes), avec un nom
          de commune agregeant les noms distincts trouves.

    Leve `CommuneIntrouvable` si aucune commune ne correspond.
    Leve `ValueError` si `code_postal` ou `strategie` sont invalides.
    """
    communes = obtenir_toutes_coordonnees_code_postal(code_postal, chemin)

    if len(communes) == 1 or strategie == "premiere":
        return communes[0]

    if strategie == "moyenne":
        noms_distincts = list(dict.fromkeys(c.nom_commune for c in communes))
        return Coordonnees(
            nom_commune=" / ".join(noms_distincts),
            code_postal=communes[0].code_postal,
            code_insee=" / ".join(dict.fromkeys(c.code_insee for c in communes)),
            latitude=mean(c.latitude for c in communes),
            longitude=mean(c.longitude for c in communes),
        )

    raise ValueError(f"Strategie inconnue : '{strategie}' (attendu : 'premiere' ou 'moyenne').")


def obtenir_coordonnees(
    ville_ou_code_postal: str, chemin: Path = CHEMIN_CACHE_COMMUNES
) -> Coordonnees | None:
    """Renvoie les coordonnees GPS correspondant a une ville ou un code postal saisi.

    Parametres
    ----------
    ville_ou_code_postal : str
        Saisie libre de l'utilisateur, ex. "Lyon", "69001", "Lyon 1er".

    Retourne
    --------
    Coordonnees | None
        Les coordonnees trouvees, ou None si aucune correspondance (y
        compris apres recherche approximative) : conformement au contrat
        d'origine de cette fonction, aucune exception n'est propagee ici
        pour une saisie simplement introuvable - voir `geocoder_par_nom`
        et `geocoder_par_code_postal` si l'on souhaite distinguer les cas
        d'erreur (via `CommuneIntrouvable`).

    Logique :
    - Saisie vide -> None.
    - Saisie composee uniquement de chiffres (4 ou 5) -> recherche par code
      postal.
    - Sinon -> recherche par nom de commune (exacte puis approximative).
    """
    if ville_ou_code_postal is None or not str(ville_ou_code_postal).strip():
        return None

    saisie = str(ville_ou_code_postal).strip()

    try:
        if re.fullmatch(r"\d{4,5}", saisie):
            return geocoder_par_code_postal(saisie, chemin=chemin)
        return geocoder_par_nom(saisie, chemin=chemin)
    except (CommuneIntrouvable, ValueError):
        # Conformement au contrat de cette fonction : on retourne None
        # plutot que de laisser remonter une exception pour un "non trouve".
        return None


# ---------------------------------------------------------------------------
# Autocompletion ville / code postal (saisie en temps reel dans le formulaire
# Streamlit) : fonctions ajoutees pour alimenter une liste deroulante qui se
# mes a jour a chaque frappe clavier de l'utilisateur.
# ---------------------------------------------------------------------------


def _libelle_suggestion(coord: Coordonnees) -> str:
    """Construit le libelle affiche dans la liste deroulante pour une commune.

    Format retenu : "Nom de la commune (code_postal)", ex. "Lyon (69001)".
    Ce format est a la fois lisible pour l'utilisateur et sans ambiguite
    (nom + code postal identifie une commune de maniere quasi unique, meme
    en cas d'homonymie entre departements).
    """
    return f"{coord.nom_commune} ({coord.code_postal})"


def rechercher_suggestions_villes(
    texte_saisi: str, limite: int = 10, chemin: Path = CHEMIN_CACHE_COMMUNES
) -> list[str]:
    """Retourne une liste de suggestions "ville (code postal)" pour l'autocompletion.

    Destinee a etre appelee a *chaque frappe clavier* de l'utilisateur dans
    le champ de saisie Streamlit (le script est reexecute a chaque rerun -
    voir le commentaire explicatif dans app.py), pour alimenter dynamiquement
    une liste deroulante de suggestions.

    Parametres
    ----------
    texte_saisi : str
        Texte partiel saisi par l'utilisateur : un debut de nom de commune
        (ex. "lyo"), ou un debut/code postal complet (ex. "6900" ou "69001"),
        insensible aux accents et a la casse.
    limite : int
        Nombre maximum de suggestions renvoyees (par defaut 10, pour rester
        lisible dans une liste deroulante).
    chemin : Path
        Chemin du CSV du referentiel (par defaut celui livre avec l'app).

    Retourne
    --------
    list[str]
        Liste de libelles formates "Nom de la commune (code_postal)", triee
        par pertinence :
        1. correspondance EXACTE en prefixe (le nom normalise, ou le code
           postal, commence exactement par le texte saisi normalise) ;
        2. puis les communes dont le nom (ou le code postal) contient
           seulement le texte saisi sans etre en prefixe ;
        3. a l'interieur de chaque groupe, triee par "importance" de la
           commune (address_count utilise comme proxy de la population),
           decroissante.
        Liste vide si `texte_saisi` est vide/blanc, ou si aucune commune ne
        correspond.

    Performance
    -----------
    S'appuie sur l'index deja construit et mis en cache module-level par
    `charger_referentiel_communes` (cf. `_CACHE`) : le CSV (~35 000 lignes)
    n'est lu et indexe qu'une seule fois par processus, quel que soit le
    nombre de frappes clavier de l'utilisateur. Chaque appel ne fait ensuite
    qu'un parcours en memoire des cles de l'index (deja normalisees), ce qui
    reste de l'ordre de quelques millisecondes meme sur 35 000 communes -
    largement compatible avec un rafraichissement a chaque frappe clavier
    dans Streamlit.
    """
    if texte_saisi is None or not str(texte_saisi).strip():
        return []

    texte_norm = _normaliser_texte(texte_saisi)
    if not texte_norm:
        return []

    # On s'assure que le referentiel est charge et indexe (une seule fois
    # par processus grace au cache module-level).
    charger_referentiel_communes(chemin)
    index_nom = _CACHE["index_nom"]
    index_code_postal = _CACHE["index_code_postal"]

    # Texte saisi "ressemblant" a un (debut de) code postal : uniquement des
    # chiffres (eventuellement avec des espaces, deja retires par la
    # normalisation du code postal ci-dessous le cas echeant).
    texte_chiffres = re.sub(r"\s+", "", str(texte_saisi).strip())
    est_recherche_code_postal = texte_chiffres.isdigit() and len(texte_chiffres) <= 5

    # candidats : dict cle=(nom_commune, code_postal) -> (coord, poids, rang_pertinence)
    # rang_pertinence : 0 = prefixe exact (meilleur), 1 = contient seulement.
    candidats: dict[tuple[str, str], tuple[Coordonnees, int, int]] = {}

    def _ajouter_candidat(coord: Coordonnees, poids: int, rang: int) -> None:
        cle = (coord.nom_commune, coord.code_postal)
        existant = candidats.get(cle)
        if existant is None or rang < existant[2] or (rang == existant[2] and poids > existant[1]):
            candidats[cle] = (coord, poids, rang)

    if est_recherche_code_postal:
        # Recherche par code postal : prefixe (ex. "690" -> "69001", "69002"...).
        for code_postal, entrees in index_code_postal.items():
            if code_postal.startswith(texte_chiffres):
                for coord, poids in entrees:
                    _ajouter_candidat(coord, poids, rang=0)
            elif texte_chiffres in code_postal:
                for coord, poids in entrees:
                    _ajouter_candidat(coord, poids, rang=1)

    # Recherche par nom de commune, meme si la saisie est numerique (certains
    # noms de communes contiennent des chiffres, ex. arrondissements) : on la
    # fait systematiquement, en plus de la recherche par code postal.
    for nom_norm, entrees in index_nom.items():
        if nom_norm.startswith(texte_norm):
            for coord, poids in entrees:
                _ajouter_candidat(coord, poids, rang=0)
        elif texte_norm in nom_norm:
            for coord, poids in entrees:
                _ajouter_candidat(coord, poids, rang=1)

    if not candidats:
        return []

    # Tri final : prefixe exact avant "contient seulement" (rang croissant),
    # puis par importance (poids = address_count) decroissante.
    candidats_tries = sorted(
        candidats.values(), key=lambda item: (item[2], -item[1])
    )

    suggestions = [_libelle_suggestion(coord) for coord, _poids, _rang in candidats_tries]
    return suggestions[: max(0, int(limite))]


def resoudre_suggestion_ville(
    libelle_suggestion: str, chemin: Path = CHEMIN_CACHE_COMMUNES
) -> Coordonnees | None:
    """Retrouve les Coordonnees exactes correspondant a un libelle de suggestion.

    A utiliser une fois que l'utilisateur a selectionne une suggestion dans
    la liste deroulante produite par `rechercher_suggestions_villes` (format
    "Nom de la commune (code_postal)"), pour obtenir sans ambiguite la
    commune exacte (et non pas re-lancer une recherche floue sur le libelle).

    Retourne None si le libelle ne correspond a aucune commune connue (cas
    normalement impossible si le libelle provient bien de
    `rechercher_suggestions_villes`, mais gere par securite).
    """
    if not libelle_suggestion or not str(libelle_suggestion).strip():
        return None

    correspondance = re.match(r"^(.*)\s\(([0-9]{4,5})\)\s*$", str(libelle_suggestion).strip())
    if not correspondance:
        # Libelle non reconnu : on retombe sur la recherche classique.
        return obtenir_coordonnees(libelle_suggestion, chemin=chemin)

    nom_commune, code_postal = correspondance.group(1).strip(), correspondance.group(2).strip()
    nom_norm_cible = _normaliser_texte(nom_commune)
    code_postal_norm = _normaliser_code_postal(code_postal)

    for coord in charger_referentiel_communes(chemin):
        if coord.code_postal == code_postal_norm and _normaliser_texte(coord.nom_commune) == nom_norm_cible:
            return coord

    # Repli : recherche classique sur le code postal seul.
    try:
        return geocoder_par_code_postal(code_postal_norm, chemin=chemin)
    except (CommuneIntrouvable, ValueError):
        return None
