"""
app.py

Point d'entree Streamlit de l'application "bonnes_affaires_app".

Organise l'interface en 5 onglets :
    1. Recherche                         - formulaire de filtres
    2. Resultats                          - annonces dans le(s) rayon(s) choisi(s), triees par score
    3. Autres (hors rayon sans livraison) - annonces ecartees des Resultats pour information
    4. Historique des prix                - evolution du prix moyen pour une recherche sauvegardee
    5. Favoris / Recherches sauvegardees  - gestion des favoris, recherches et alertes

Ce fichier ne contient volontairement AUCUNE logique metier : il delegue
tout aux modules dedies (connecteurs/, geocodage.py, distance.py,
scoring.py, filtres.py, favoris.py, alertes.py, historique_prix.py).
Les appels effectifs a ces modules sont indiques par des TODO : a ce stade,
ils leveraient NotImplementedError puisque seules les signatures existent.
L'interface (widgets) est en revanche deja posee et fonctionnelle.
"""

from __future__ import annotations

import streamlit as st

from filtres import FiltresRecherche, ModeAffichage, PresetAffichage, VilleRayon

# TODO (V1): une fois les modules implementes, importer egalement :
# from connecteurs.leboncoin import LeBonCoinConnecteur
# from connecteurs.vinted import VintedConnecteur
# from geocodage import obtenir_coordonnees
# from distance import annonce_dans_perimetre, distance_minimale
# from scoring import calculer_prix_moyen_occasion, calculer_score_bonne_affaire, classer_annonces_par_score
# from favoris import ajouter_favori, lister_favoris, sauvegarder_recherche, lister_recherches_sauvegardees
# from alertes import creer_alerte, lister_alertes
# from historique_prix import enregistrer_point_historique, charger_historique


SITES_DISPONIBLES = ["leboncoin", "vinted"]  # TODO (V3): ajouter "facebook_marketplace"

ETATS_PRODUIT_DISPONIBLES = [
    "neuf_avec_etiquette",
    "neuf_sans_etiquette",
    "tres_bon_etat",
    "bon_etat",
    "satisfaisant",
    "pour_pieces",
]


def initialiser_etat_session() -> None:
    '''Initialise les valeurs par defaut dans st.session_state si absentes.

    Streamlit reexecute le script a chaque interaction : st.session_state
    permet de conserver dans le temps la liste des villes ajoutees par
    l'utilisateur (sinon elle serait reinitialisee a chaque clic).
    '''
    if "villes_rayons" not in st.session_state:
        # Liste de dicts {"ville": str, "rayon_km": int} manipulee par l'UI,
        # convertie en liste de VilleRayon au moment de lancer la recherche.
        st.session_state.villes_rayons = []


def section_formulaire_recherche() -> FiltresRecherche | None:
    '''Affiche le formulaire complet de l'onglet "Recherche" et renvoie les filtres saisis.

    Retourne un objet FiltresRecherche si l'utilisateur a clique sur le
    bouton de lancement de recherche, sinon None (formulaire pas encore
    valide lors de ce rerun).

    TODO (V1): une fois le formulaire valide, construire reellement l'objet
    FiltresRecherche (actuellement, cette fonction construit l'objet mais la
    recherche elle-meme - section_resultats - n'est pas encore cablee aux
    connecteurs).
    '''
    st.header("Recherche")

    mot_cle = st.text_input(
        "Mot-cle",
        placeholder="ex. velo electrique, console retro, ...",
        help="Terme recherche sur les sites selectionnes.",
    )

    col_prix_min, col_prix_max = st.columns(2)
    with col_prix_min:
        prix_min = st.number_input("Prix minimum (EUR)", min_value=0.0, value=0.0, step=5.0)
    with col_prix_max:
        prix_max = st.number_input("Prix maximum (EUR)", min_value=0.0, value=0.0, step=5.0)
        # TODO (V1): si prix_max == 0.0, le considerer comme "pas de maximum" (None)
        # plutot qu'un vrai plafond de 0 EUR -- a clarifier dans filtres.valider().

    etat_minimum = st.selectbox(
        "Etat minimum accepte",
        options=["(peu importe)"] + ETATS_PRODUIT_DISPONIBLES,
        help="Les annonces d'un etat inferieur a ce seuil seront ecartees.",
    )

    st.subheader("Mots-cles inclus / exclus")
    col_inclus, col_exclus = st.columns(2)
    with col_inclus:
        mots_cles_inclus_brut = st.text_input(
            "Mots-cles obligatoires (separes par des virgules)",
            placeholder="ex. electrique, 26 pouces",
        )
    with col_exclus:
        mots_cles_exclus_brut = st.text_input(
            "Mots-cles a exclure (separes par des virgules)",
            placeholder="ex. casse, pour pieces",
        )

    st.subheader("Sites a interroger")
    multisite = st.checkbox("Multisite (interroger tous les sites disponibles)", value=True)
    sites_coches = st.multiselect(
        "Sites specifiques (ignore si Multisite est coche)",
        options=SITES_DISPONIBLES,
        default=SITES_DISPONIBLES,
        disabled=multisite,
    )

    st.subheader("Zones de recherche (villes + rayon)")
    st.caption("Ajoutez une ou plusieurs villes ; chaque ville dispose de son propre rayon (1-100 km).")

    texte_saisi = st.text_input("Ville ou code postal", key="saisie_ville_autocomplete")

    from geocodage import rechercher_suggestions_villes
    suggestions = rechercher_suggestions_villes(texte_saisi)

    ville_selectionnee = None
    if suggestions:
        ville_selectionnee = st.selectbox("Suggestions", suggestions, key="selectbox_suggestions_ville")
    elif texte_saisi:
        st.info("Aucune commune trouvee")

    with st.form("ajout_ville", clear_on_submit=True):
        col_rayon, col_ajout = st.columns([2, 1])
        with col_rayon:
            nouveau_rayon = st.slider("Rayon (km)", min_value=1, max_value=100, value=15, key="champ_nouveau_rayon")
        with col_ajout:
            ajouter = st.form_submit_button("Ajouter")

    nouvelle_ville = ville_selectionnee if ville_selectionnee else texte_saisi

    if ajouter and nouvelle_ville.strip():
        # TODO (V1): valider la ville via geocodage.obtenir_coordonnees avant
        # de l'ajouter (afficher une erreur si la ville est introuvable).
        st.session_state.villes_rayons.append({"ville": nouvelle_ville.strip(), "rayon_km": nouveau_rayon})

    for index, zone in enumerate(st.session_state.villes_rayons):
        col_affichage, col_suppr = st.columns([5, 1])
        with col_affichage:
            st.write(f"- {zone['ville']} (rayon {zone['rayon_km']} km)")
        with col_suppr:
            if st.button("Retirer", key=f"retirer_zone_{index}"):
                st.session_state.villes_rayons.pop(index)
                st.rerun()

    accepter_si_livraison_disponible = st.checkbox(
        "Inclure dans les Resultats les annonces hors rayon si la livraison est proposee",
        value=True,
        help="Si decoche, ces annonces apparaitront uniquement dans l'onglet 'Autres'.",
    )

    st.subheader("Mode d'affichage des resultats")
    preset = st.radio(
        "Preset rapide",
        options=[PresetAffichage.VUE_RAPIDE.value, PresetAffichage.VUE_COMPARATIVE.value, "personnalise"],
        format_func=lambda v: {
            PresetAffichage.VUE_RAPIDE.value: "Vue rapide (toutes annonces melangees, triees par score)",
            PresetAffichage.VUE_COMPARATIVE.value: "Vue comparative (un bloc de resultats par site)",
            "personnalise": "Personnalise",
        }[v],
        horizontal=True,
    )
    if preset == PresetAffichage.VUE_RAPIDE.value:
        mode_affichage = ModeAffichage.MELANGE
    elif preset == PresetAffichage.VUE_COMPARATIVE.value:
        mode_affichage = ModeAffichage.SEPARE
    else:
        mode_affichage_brut = st.radio(
            "Mode d'affichage personnalise",
            options=[ModeAffichage.MELANGE.value, ModeAffichage.SEPARE.value],
            format_func=lambda v: "Melange" if v == ModeAffichage.MELANGE.value else "Separe par site",
            horizontal=True,
        )
        mode_affichage = ModeAffichage(mode_affichage_brut)

    # Bloc "Fiabilite du vendeur" (st.subheader + st.slider seuil_fiabilite_vendeur_min)
    # supprime : le filtrage par seuil de fiabilite est remplace par l'affichage
    # d'un badge colore par annonce dans section_resultats() (cf. plus bas).

    lancer = st.button("Lancer la recherche", type="primary")

    if not lancer:
        return None

    villes_rayons_objets = [
        VilleRayon(ville_ou_code_postal=zone["ville"], rayon_km=zone["rayon_km"])
        for zone in st.session_state.villes_rayons
    ]

    filtres = FiltresRecherche(
        mot_cle=mot_cle,
        prix_min=prix_min or None,
        prix_max=prix_max or None,
        etat_minimum=None if etat_minimum == "(peu importe)" else etat_minimum,
        mots_cles_inclus=[m.strip() for m in mots_cles_inclus_brut.split(",") if m.strip()],
        mots_cles_exclus=[m.strip() for m in mots_cles_exclus_brut.split(",") if m.strip()],
        villes_rayons=villes_rayons_objets,
        accepter_si_livraison_disponible=accepter_si_livraison_disponible,
        multisite=multisite,
        sites_actifs=sites_coches,
        seuil_fiabilite_vendeur_min=None,  # Variable/slider supprimee : plus de filtrage par seuil ici,
        # la fiabilite est desormais affichee via un badge par annonce (section_resultats()).
        mode_affichage=mode_affichage,
    )
    return filtres


def afficher_badge_fiabilite_vendeur(score_fiabilite_vendeur: float | None) -> None:
    '''Affiche un badge HTML colore resumant la fiabilite du vendeur.

    HYPOTHESE D'ECHELLE : score_fiabilite_vendeur est exprime sur une echelle
    0-100 (cf. le commentaire du champ dans connecteurs/base.py : "0-100, selon
    donnees disponibles sur le site"). Les seuils ci-dessous (70 et 40) sont
    donc a comprendre comme des pourcentages, PAS comme des fractions 0-1.
    Si un connecteur venait a fournir une echelle 0-1, il faudrait soit
    normaliser le score avant l'appel, soit adapter les seuils (0.7 et 0.4).

    Parametres
    ----------
    score_fiabilite_vendeur : float | None
        Score de fiabilite du vendeur, ou None si l'information n'est pas
        disponible sur le site d'origine de l'annonce.
    '''
    style_commun = (
        "display:inline-block; padding:2px 10px; border-radius:12px; "
        "color:white; font-size:0.85em; font-weight:600;"
    )

    if score_fiabilite_vendeur is None:
        couleur = "#9e9e9e"  # gris
        libelle = "Fiabilite inconnue"
    elif score_fiabilite_vendeur >= 70:
        couleur = "#2e7d32"  # vert
        libelle = "✅ Bon vendeur"
    elif score_fiabilite_vendeur >= 40:
        couleur = "#f57c00"  # orange
        libelle = "⚠️ Fiabilite moyenne"
    else:
        couleur = "#c62828"  # rouge
        libelle = "❌ Attention vendeur"

    st.markdown(
        f'<span style="{style_commun} background-color:{couleur};">{libelle}</span>',
        unsafe_allow_html=True,
    )


def afficher_carte_annonce(annonce) -> None:
    '''Affiche une "carte" simple pour une annonce (titre, prix, ville) et son badge de fiabilite.

    Parametres
    ----------
    annonce : connecteurs.base.Annonce
        Annonce normalisee a afficher.
    '''
    col_infos, col_badge = st.columns([4, 1])
    with col_infos:
        st.subheader(annonce.titre)
        ville_affichee = annonce.ville if annonce.ville else "Ville inconnue"
        st.write(f"{annonce.prix:.2f} EUR - {ville_affichee}")
    with col_badge:
        afficher_badge_fiabilite_vendeur(annonce.score_fiabilite_vendeur)
    st.divider()


def afficher_liste_annonces(annonces: list) -> None:
    '''Boucle d'affichage des annonces : carte (titre, prix, ville) + badge de fiabilite.

    Fonction prete a etre appelee dans section_resultats() dès que les
    connecteurs renverront une vraie liste d'Annonce. Tant que ce n'est pas
    le cas, section_resultats() lui passe une liste vide et un st.info de
    repli est affiche.

    Parametres
    ----------
    annonces : list[connecteurs.base.Annonce]
        Liste des annonces a afficher, deja filtrees/triees en amont.
    '''
    if not annonces:
        st.info("Aucune annonce a afficher pour le moment.")
        return
    for annonce in annonces:
        afficher_carte_annonce(annonce)


def section_resultats(filtres: FiltresRecherche | None) -> None:
    '''Affiche l'onglet "Resultats" : annonces dans le(s) rayon(s), triees par score.

    TODO (V1):
    - Si filtres est None, afficher un message invitant a lancer une recherche.
    - Sinon, instancier les connecteurs correspondant a filtres.sites_a_interroger(),
      appeler .rechercher(filtres) sur chacun (en gerant les erreurs par site
      independamment, cf. ARCHITECTURE.md section Limites).
    - Filtrer geographiquement avec distance.annonce_dans_perimetre, en
      separant les annonces "dans le rayon" des annonces "hors rayon".
    - Appliquer les filtres mots-cles inclus/exclus, etat, fiabilite vendeur.
    - Appeler scoring.classer_annonces_par_score sur les annonces retenues.
    - Afficher selon filtres.mode_affichage : une liste unique triee
      (MELANGE) ou un bloc par site (SEPARE).
    - Proposer un bouton "Ajouter aux favoris" par annonce affichee
      (favoris.ajouter_favori).
    '''
    st.header("Resultats")
    if filtres is None:
        st.info("Renseignez vos criteres dans l'onglet 'Recherche' puis lancez une recherche.")
        return
    st.warning(
        "Les connecteurs ne sont pas encore implementes (squelette V1). "
        "Cette section affichera ici les annonces triees par score 'bonne affaire'."
    )

    # TODO: remplacer par la vraie liste d'annonces renvoyee par les connecteurs
    # (une fois scoring.classer_annonces_par_score et le filtrage geographique
    # branches). En attendant, on passe une liste vide : afficher_liste_annonces
    # se charge d'afficher un st.info de repli si la liste est vide.
    annonces: list = []
    afficher_liste_annonces(annonces)


def section_autres(filtres: FiltresRecherche | None) -> None:
    '''Affiche l'onglet "Autres" : annonces hors rayon et sans option de livraison.

    TODO (V1): reprendre les annonces ecartees lors du filtrage geographique
    de section_resultats (hors rayon ET sans livraison disponible), les
    afficher ici a titre informatif, avec leur distance_minimale calculee
    via distance.distance_minimale.
    '''
    st.header("Autres (hors rayon, sans livraison)")
    if filtres is None:
        st.info("Renseignez vos criteres dans l'onglet 'Recherche' puis lancez une recherche.")
        return
    st.warning("A implementer en V1, une fois les connecteurs et le filtrage geographique en place.")


def section_historique_prix() -> None:
    '''Affiche l'onglet "Historique des prix" : graphique d'evolution pour une recherche sauvegardee.

    TODO (V2):
    - Lister les recherches sauvegardees disponibles (favoris.lister_recherches_sauvegardees).
    - Permettre a l'utilisateur d'en choisir une.
    - Charger l'historique (historique_prix.charger_historique) et tracer un
      graphique (ex. st.line_chart) de l'evolution du prix moyen dans le temps.
    '''
    st.header("Historique des prix")
    st.warning("Fonctionnalite prevue en V2 (necessite favoris.py et historique_prix.py).")


def section_favoris_et_recherches() -> None:
    '''Affiche l'onglet "Favoris / Recherches sauvegardees".

    TODO (V2):
    - Lister les annonces favorites (favoris.lister_favoris) avec possibilite
      de les retirer (favoris.retirer_favori).
    - Lister les recherches sauvegardees (favoris.lister_recherches_sauvegardees)
      avec possibilite de les recharger dans l'onglet Recherche ou de les
      supprimer (favoris.supprimer_recherche_sauvegardee).
    - Lister les alertes configurees (alertes.lister_alertes), permettre d'en
      creer une nouvelle (alertes.creer_alerte) et de verifier manuellement
      les alertes (alertes.verifier_alertes_manuellement).
    '''
    st.header("Favoris / Recherches sauvegardees")
    st.warning("Fonctionnalite prevue en V2 (necessite favoris.py et alertes.py).")


def main() -> None:
    '''Point d'entree de l'application Streamlit.'''
    st.set_page_config(page_title="Bonnes affaires", page_icon=":mag:", layout="wide")
    st.title("Recherche de bonnes affaires - occasion")
    st.caption("Usage personnel - Le Bon Coin + Vinted (V1). Facebook Marketplace prevu en V3.")

    initialiser_etat_session()

    onglet_recherche, onglet_resultats, onglet_autres, onglet_historique, onglet_favoris = st.tabs(
        ["Recherche", "Resultats", "Autres", "Historique des prix", "Favoris / Recherches sauvegardees"]
    )

    with onglet_recherche:
        filtres = section_formulaire_recherche()
        # TODO (V1): conserver `filtres` dans st.session_state pour que les
        # autres onglets (Resultats, Autres) y accedent meme apres un rerun
        # Streamlit ne declenche pas par le bouton "Lancer la recherche".
        if filtres is not None:
            st.session_state.derniers_filtres = filtres

    filtres_courants = st.session_state.get("derniers_filtres")

    with onglet_resultats:
        section_resultats(filtres_courants)

    with onglet_autres:
        section_autres(filtres_courants)

    with onglet_historique:
        section_historique_prix()

    with onglet_favoris:
        section_favoris_et_recherches()


if __name__ == "__main__":
    main()
