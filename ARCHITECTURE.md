# ARCHITECTURE.md

## Projet : bonnes_affaires_app

Application Streamlit à usage **strictement personnel** permettant de rechercher de bonnes
affaires sur des sites de petites annonces d'occasion (Le Bon Coin, Vinted en V1 ; Facebook
Marketplace prévu en V3). L'application interroge les sites à faible fréquence (usage manuel,
pas de scraping massif ni automatisé en continu), calcule un score de "bonne affaire" et
permet de filtrer/trier les résultats selon des critères personnels (prix, localisation,
mots-clés, fiabilité du vendeur, etc.).

---

## 1. Structure globale du projet

```
bonnes_affaires_app/
│
├── app.py                     # Point d'entrée Streamlit (interface utilisateur, onglets)
│
├── connecteurs/                # Un module par site d'annonces
│   ├── __init__.py
│   ├── base.py                 # Interface commune (classe abstraite) à tous les connecteurs
│   ├── leboncoin.py             # Connecteur spécifique à Le Bon Coin
│   └── vinted.py                # Connecteur spécifique à Vinted
│
├── geocodage.py                # Conversion ville / code postal -> coordonnées GPS (data.gouv.fr)
├── distance.py                 # Calcul de distances (formule de Haversine) annonce <-> villes
├── scoring.py                  # Calcul du score "bonne affaire" (prix annonce vs marché)
├── filtres.py                  # Structures de données représentant les filtres de recherche
├── favoris.py                   # Gestion locale des favoris et recherches sauvegardées
├── alertes.py                   # Gestion locale des alertes produit
├── historique_prix.py           # Historique local des prix moyens par recherche
│
├── data/                        # Données locales persistées (créé/peuplé à l'exécution)
│   ├── communes_france.csv       # Cache local du référentiel des communes (data.gouv.fr)
│   ├── favoris.json               # Annonces favorites + recherches sauvegardées
│   ├── alertes.json               # Alertes produit configurées par l'utilisateur
│   └── historique_prix.json       # Historique des prix moyens observés par recherche
│
├── requirements.txt             # Dépendances Python de la V1
└── ARCHITECTURE.md              # Ce document
```

### Rôle de chaque fichier

- **app.py** : seul fichier qui importe `streamlit`. Construit l'interface (formulaire de
  filtres + onglets de résultats), orchestre les appels aux connecteurs, au géocodage, au
  calcul de distance et au scoring, et affiche les résultats. Ne contient aucune logique
  métier complexe : il délègue tout aux modules dédiés (séparation claire UI / logique).
- **connecteurs/base.py** : définit la classe abstraite `ConnecteurAnnonces` que chaque site
  doit implémenter (méthodes `rechercher()`, `nom_site`, normalisation du format d'annonce).
  C'est le contrat qui permettra d'ajouter Facebook Marketplace (V3) sans toucher au reste de
  l'application.
- **connecteurs/leboncoin.py** / **connecteurs/vinted.py** : implémentations concrètes, chacune
  responsable de la construction des requêtes, du parsing (HTML ou JSON selon le site) et de
  la conversion vers le format d'annonce normalisé (`Annonce`, défini dans `base.py`).
- **geocodage.py** : convertit une ville ou un code postal saisi par l'utilisateur en
  coordonnées GPS (latitude/longitude), en s'appuyant sur un fichier CSV public des communes
  françaises (data.gouv.fr), téléchargé une fois puis mis en cache localement dans
  `data/communes_france.csv`.
- **distance.py** : calcule la distance en kilomètres entre deux points GPS (formule de
  Haversine) et détermine si une annonce se trouve dans le rayon choisi pour une ou plusieurs
  villes.
- **scoring.py** : calcule un score "bonne affaire" en comparant le prix d'une annonce au prix
  moyen du marché de l'occasion et au prix moyen du neuf pour un même type de produit.
- **filtres.py** : dataclasses représentant l'ensemble des critères de recherche saisis par
  l'utilisateur (mot-clé, prix, état, villes+rayons, sites, mode d'affichage, etc.), utilisées
  comme objet de passage entre `app.py` et les connecteurs/le scoring.
- **favoris.py** / **alertes.py** : persistance locale (JSON, éventuellement migrable vers
  SQLite) des annonces favorites, recherches sauvegardées et alertes produit.
- **historique_prix.py** : enregistre, à chaque recherche effectuée, le prix moyen observé afin
  d'alimenter l'onglet "Historique des prix" (évolution dans le temps).
- **data/** : dossier de données locales. Il n'est jamais versionné avec des données
  personnelles sensibles ; seul `communes_france.csv` est un référentiel public.

---

## 2. Découpage en modules (détail)

### 2.1 `connecteurs/`

Chaque site d'annonces a des contraintes différentes (structure HTML, pagination, besoin ou
non de JavaScript, format JSON interne, etc.). Pour que l'application reste maintenable et
extensible (notamment pour accueillir Facebook Marketplace plus tard sans tout réécrire),
chaque connecteur respecte une interface commune définie dans `base.py` :

- Une **dataclass `Annonce`** normalisée (titre, prix, ville, code postal, latitude/longitude
  si connue, URL, état déclaré, date de publication, nom/fiabilité du vendeur si disponible,
  mode de livraison disponible ou non, site d'origine, photo principale...).
- Une **classe abstraite `ConnecteurAnnonces`** avec :
  - une méthode `rechercher(filtres: FiltresRecherche) -> list[Annonce]`,
  - un attribut `nom_site: str`,
  - des méthodes utilitaires protégées pour construire l'URL de recherche et parser une page
    de résultats, que chaque connecteur concret personnalise.

`leboncoin.py` et `vinted.py` héritent de `ConnecteurAnnonces` et implémentent le détail propre
à chaque site (construction d'URL, en-têtes HTTP, parsing BeautifulSoup ou appel d'API interne
JSON, pagination, limitation du nombre de requêtes). Comme indiqué dans les limites (section 4),
ce sont les fichiers les plus susceptibles de nécessiter une maintenance régulière.

### 2.2 `geocodage.py`

But : transformer une saisie libre de l'utilisateur ("Lyon", "69001", "Lyon 1er") en
coordonnées GPS exploitables par `distance.py`.

Approche retenue :
- Téléchargement (une seule fois, puis cache local) du fichier CSV public des communes
  françaises mis à disposition sur data.gouv.fr / API Géo, contenant pour chaque commune :
  nom, code postal, code INSEE, latitude, longitude, population.
- Chargement de ce CSV en mémoire (ou requête indexée) pour permettre une recherche rapide
  par nom de ville (normalisé, sans accents, insensible à la casse) ou par code postal.
- Fonction `obtenir_coordonnees(ville_ou_cp: str) -> Coordonnees | None` qui renvoie les
  coordonnées correspondantes, avec gestion des cas ambigus (plusieurs communes de même nom).

### 2.3 `distance.py`

But : déterminer si une annonce correspond à une zone géographique choisie par l'utilisateur.

- Fonction `distance_haversine(lat1, lon1, lat2, lon2) -> float` : distance en kilomètres entre
  deux points GPS, selon la formule de Haversine (prend en compte la courbure terrestre).
- Fonction `annonce_dans_perimetre(annonce, villes_rayons) -> bool` : vérifie si l'annonce est
  à l'intérieur d'au moins un des couples (ville, rayon_km) choisis par l'utilisateur.
- Fonction `distance_minimale(annonce, villes_rayons) -> float` : renvoie la distance la plus
  courte entre l'annonce et l'une des villes choisies (utile pour le tri et pour l'onglet
  "Autres" qui liste les annonces hors rayon mais disponibles en livraison).

### 2.4 `scoring.py`

But : attribuer à chaque annonce un score "bonne affaire" permettant de trier les résultats.

Logique prévue (V1, simple) :
- Comparer le prix de l'annonce au **prix moyen de l'occasion** pour un produit similaire
  (basé sur l'historique local constitué par `historique_prix.py` et/ou sur une estimation
  calculée à partir des résultats de la recherche courante).
- Comparer également au **prix moyen du neuf** si disponible (saisi manuellement ou renseigné
  dans une table de référence future), afin de mettre en évidence les décotes importantes.
- Produire un score normalisé (ex. pourcentage d'écart par rapport au marché de l'occasion)
  et une étiquette qualitative ("Très bonne affaire", "Prix correct", "Cher").

Fonctions clairement nommées, par exemple :
- `calculer_prix_moyen_occasion(annonces: list[Annonce]) -> float`
- `calculer_score_bonne_affaire(annonce: Annonce, prix_moyen_occasion: float, prix_moyen_neuf: float | None) -> ScoreBonneAffaire`
- `classer_annonces_par_score(annonces: list[Annonce]) -> list[Annonce]`

TODO explicitement laissés dans le fichier pour les évolutions futures :
- Détection de lots / bundles (plusieurs objets vendus ensemble à un prix global) et ajustement
  du score en conséquence (division du prix par le nombre d'objets estimé).
- Prise en compte de l'état déclaré du produit dans le calcul du prix moyen (un produit "comme
  neuf" ne devrait pas être comparé de la même façon qu'un produit "pour pièces").

### 2.5 `filtres.py`

But : centraliser, sous forme de **dataclasses**, l'ensemble des critères de recherche afin
d'avoir un seul objet transmis entre l'interface (`app.py`), les connecteurs et le scoring.

Contenu prévu :
- `VilleRayon` : une ville/code postal choisie + un rayon en kilomètres (1 à 100 km).
- `ModeAffichage` : énumération `MELANGE` (toutes les annonces multisite triées ensemble) ou
  `SEPARE` (un bloc de résultats par site), avec deux "presets" évoqués par l'utilisateur
  (ex. preset "Vue rapide mélangée triée par score" et preset "Vue comparative par site").
- `FiltresRecherche` : dataclass regroupant mot-clé, prix min/max, état du produit, liste de
  `VilleRayon`, sites cochés + case "Multisite", mots-clés inclus/exclus, seuil minimal de
  fiabilité vendeur, mode d'affichage.

### 2.6 `favoris.py` et `alertes.py`

But : persistance locale simple, sans base de données serveur (fichier JSON suffisant pour un
usage personnel à faible fréquence ; une migration vers SQLite est envisageable si le volume de
données augmente, les fonctions sont écrites pour permettre ce changement sans impacter le
reste de l'application).

- `favoris.py` : ajouter/retirer une annonce des favoris, lister les favoris, sauvegarder une
  recherche (= un objet `FiltresRecherche` nommé) et la recharger plus tard.
- `alertes.py` : créer une alerte (recherche sauvegardée + condition, ex. "prix sous X€" ou
  "nouvelle annonce correspondant aux filtres"), lister/supprimer les alertes. En V1, aucune
  notification automatique n'est envoyée (pas de tâche planifiée) : la vérification se fait
  manuellement, lors de l'ouverture de l'application. L'automatisation (ex. notification email)
  est une évolution future hors scope V1/V2 immédiat.

### 2.7 `historique_prix.py`

But : conserver dans le temps le prix moyen observé pour chaque recherche effectuée, afin
d'alimenter l'onglet "Historique des prix" (graphique d'évolution).

- `enregistrer_point_historique(nom_recherche: str, prix_moyen: float, date: datetime) -> None`
- `charger_historique(nom_recherche: str) -> list[PointHistorique]`

### 2.8 `app.py`

Point d'entrée Streamlit. Organisé en 5 onglets :
1. **Recherche** : formulaire de filtres (mot-clé, prix min/max, état, sites + case
   "Multisite", ajout de plusieurs villes avec slider de rayon 1-100 km chacune, mode
   d'affichage mélangé/séparé avec presets, mots-clés inclus/exclus, seuil de fiabilité
   vendeur).
2. **Résultats** : annonces dans le(s) rayon(s) choisi(s), triées par score bonne affaire,
   affichage mélangé ou séparé par site selon le filtre choisi.
3. **Autres** : annonces hors rayon géographique mais ne proposant pas de livraison (donc
   normalement exclues des résultats pertinents), affichées à part pour information.
4. **Historique des prix** : graphique d'évolution du prix moyen pour une recherche
   sauvegardée, basé sur `historique_prix.py`.
5. **Favoris / Recherches sauvegardées** : gestion des annonces favorites et des recherches
   sauvegardées / alertes.

---

## 3. Flux de données complet

1. L'utilisateur remplit le formulaire de l'onglet **Recherche** dans `app.py`.
2. `app.py` construit un objet `FiltresRecherche` (défini dans `filtres.py`) à partir des
   widgets Streamlit (mot-clé, prix, villes/rayons, sites cochés, etc.).
3. Pour chaque ville saisie dans les filtres, `geocodage.py` convertit le nom de ville / code
   postal en coordonnées GPS (`obtenir_coordonnees`), en s'appuyant sur le cache local
   `data/communes_france.csv`.
4. `app.py` instancie les connecteurs correspondant aux sites cochés (ou tous si "Multisite"
   est cochée) et appelle `rechercher(filtres)` sur chacun, ce qui renvoie une liste
   d'`Annonce` normalisées (classe commune définie dans `connecteurs/base.py`).
5. Les annonces récupérées sont filtrées géographiquement grâce à `distance.py`
   (`annonce_dans_perimetre`), en les séparant en deux groupes :
   - annonces dans au moins un rayon choisi -> candidates pour l'onglet Résultats,
   - annonces hors rayon sans option de livraison -> onglet Autres.
6. Les annonces candidates sont filtrées davantage selon les mots-clés inclus/exclus, l'état,
   le seuil de fiabilité vendeur.
7. `scoring.py` calcule, pour les annonces restantes, le prix moyen de l'occasion observé dans
   le lot de résultats (et le prix moyen du neuf si disponible), puis un score "bonne affaire"
   par annonce. Les annonces sont triées par score décroissant.
8. `historique_prix.py` enregistre le prix moyen de la recherche courante (si l'utilisateur le
   souhaite / si la recherche est nommée), pour nourrir l'onglet Historique des prix.
9. `app.py` affiche les résultats classés dans l'onglet **Résultats** (mode mélangé ou séparé
   selon le filtre choisi), les annonces hors rayon dans **Autres**, et permet d'ajouter une
   annonce aux favoris (`favoris.py`) directement depuis la liste affichée.
10. L'utilisateur peut, à tout moment, sauvegarder la recherche courante (`favoris.py`), créer
    une alerte associée (`alertes.py`), ou consulter l'historique des prix pour une recherche
    déjà sauvegardée.

---

## 4. Limites connues à ce stade

- **Absence d'API officielle** : Le Bon Coin et Vinted ne fournissent pas d'API publique
  stable destinée aux développeurs tiers. Les connecteurs s'appuient donc sur le parsing de
  pages HTML ou d'appels JSON internes aux sites, ce qui est intrinsèquement fragile.
- **Dépendance à la structure HTML/JSON des sites** : toute modification de la structure des
  pages ou des endpoints internes des sites casse potentiellement le connecteur concerné. Les
  fichiers `connecteurs/leboncoin.py` et `connecteurs/vinted.py` devront être mis à jour
  régulièrement et testés manuellement avant chaque usage important.
- **Nécessité de délais entre requêtes** : pour rester dans un usage strictement personnel,
  raisonnable et respectueux des sites (pas de scraping massif), chaque connecteur doit
  introduire un délai (ex. quelques secondes) entre deux requêtes, limiter le nombre de pages
  consultées par recherche, et ne jamais lancer de recherches automatiques en boucle/planifiées.
- **Pas de garantie de disponibilité** : si un site bloque temporairement les requêtes
  automatisées (CAPTCHA, blocage d'IP, changement de conditions d'utilisation), le connecteur
  concerné peut devenir indisponible sans préavis ; l'application doit gérer cet échec sans
  bloquer les autres connecteurs (isolation des erreurs par site).
- **Qualité du géocodage** : certaines communes ont des homonymies (plusieurs communes de même
  nom dans des départements différents) ; en V1, le choix du bon résultat peut nécessiter une
  précision supplémentaire (code postal) de la part de l'utilisateur.
- **Scoring volontairement simple en V1** : le calcul du prix moyen "occasion" se base
  principalement sur les résultats de la recherche courante (échantillon potentiellement
  faible et biaisé), et le prix moyen "neuf" n'est pas encore automatisé (pas de connecteur
  magasin neuf) : la pertinence du score s'améliorera avec l'historique accumulé (V2) et une
  éventuelle source de prix neuf (évolution future).
- **Pas de prise en compte des lots/bundles en V1** : une annonce vendant plusieurs objets au
  même prix sera comparée au prix d'un seul objet, ce qui peut fausser le score (TODO identifié
  dans `scoring.py`).

---

## 5. Plan d'implémentation en versions successives

### V1 — Socle fonctionnel minimal
- Connecteurs Le Bon Coin + Vinted (`connecteurs/base.py`, `leboncoin.py`, `vinted.py`).
- Filtres de base : mot-clé, prix min/max, état, mots-clés inclus/exclus.
- Géolocalisation multi-villes avec rayon (1-100 km) par ville (`geocodage.py`, `distance.py`).
- Gestion de la livraison : annonces hors rayon mais livrables -> onglet Résultats ; hors rayon
  et non livrables -> onglet Autres.
- Score "bonne affaire" simple basé sur le prix moyen occasion observé dans les résultats
  (`scoring.py`, version basique sans historique long terme ni lots).
- Interface Streamlit avec les onglets Recherche / Résultats / Autres (les onglets Historique
  des prix et Favoris sont présents dans l'UI mais peuvent rester minimalistes/vides en V1).

### V2 — Suivi et confort d'usage
- Historique des prix persistant (`historique_prix.py`) avec graphique d'évolution.
- Favoris et recherches sauvegardées pleinement fonctionnels (`favoris.py`).
- Alertes produit (`alertes.py`) : création, consultation, suppression ; vérification manuelle
  au lancement de l'application (pas encore de notification automatique en tâche de fond).
- Amélioration du score "bonne affaire" grâce à l'historique accumulé (comparaison dans le
  temps, pas uniquement sur l'échantillon de la recherche courante).

### V3 — Extension et affinage
- Ajout du connecteur Facebook Marketplace (`connecteurs/facebook_marketplace.py`), en
  respectant l'interface `ConnecteurAnnonces` définie en V1, sans modification du reste de
  l'application.
- Détection de lots/bundles dans `scoring.py` (plusieurs objets vendus ensemble) et ajustement
  du score en conséquence.
- Pistes ouvertes (non engagées) : notifications automatiques pour les alertes, prix moyen du
  neuf automatisé via une source externe, export des résultats.
