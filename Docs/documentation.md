# Documentation du projet

## 1. Présentation

Ce projet a pour objectif de collecter des informations publiées en ligne au sujet d'artistes, de médias ou d'événements culturels africains, puis d'utiliser ces données pour identifier des événements et générer des marchés de prédiction.

Le pipeline combine :

1. la collecte de publications Facebook et Instagram ;
2. l'extraction des métadonnées et des images associées ;
3. la consolidation des données dans des fichiers CSV ;
4. l'analyse des publications par un modèle Gemini ;
5. la génération d'événements, de marchés et de probabilités estimées.

La collecte dépend de l'accès aux plateformes et peut nécessiter des sessions authentifiées. Les fonctionnalités d'analyse par IA nécessitent également un identifiant d'accès au service Gemini.

## 2. Organisation du projet

- `config/` : fichiers de session utilisés pour l'accès à Facebook et Instagram.
- `contexts/` : éléments de contexte utilisés pour les traitements.
- `data/` : publications collectées, images, métadonnées, profils et résultats générés.
-`data/extracted_posts` : contient les publications extraites
-`data/Save_csv` : contient les informations issues des traitements
- `info/` : documentation et fichier de dépendances d'origine.
- `modules/` : fonctions principales du projet.
- `main.py` : contient une fonction permettant d'effectuer tout le traitement IA à partir d'un dossier posts.
- `collecte.py` : lancement d'une campagne de collecte configurée pour un profil ou un hashtag.
- `analyse_predictions.py` : script d'analyse des résultats de prédiction.
- `1_setup_sessions.py` : préparation de sessions navigateur avec Playwright.
- `assistant_code/` : espace de travail séparé pour la documentation et les ajouts de l'assistant.

## 3. Déroulement général

### 3.1. Préparation des sessions

Les modules qui utilisent Playwright peuvent s'appuyer sur des sessions sauvegardées dans `config/`. Il s'agit notamment de fichiers de type `state_facebook.json` et `state_instagram.json`.

Ces fichiers sont des fichiers de session Playwright (Storage State) ; ils contiennent des cookies et parfois des données de `localStorage` du navigateur. Les valeurs réelles ne doivent jamais être intégrées dans la documentation.

Exemple minimal, anonymisé, de `state_facebook.json` :

```json
{
  "cookies": [
    {
      "name": "sessionid",
      "value": "string_value",
      "domain": ".facebook.com",
      "path": "/",
      "expires": 1700000000.0,
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    }
  ],
  "origins": [
    {
      "origin": "https://www.facebook.com",
      "localStorage": [
        {
          "name": "example_key",
          "value": "{\"some\":\"value\"}"
        }
      ]
    }
  ]
}
```

Exemple minimal, anonymisé, de `state_instagram.json` :

```json
{
  "cookies": [
    {
      "name": "sessionid",
      "value": "string_value",
      "domain": ".instagram.com",
      "path": "/",
      "expires": 1700000000.0,
      "httpOnly": true,
      "secure": true,
      "sameSite": "None"
    }
  ],
  "origins": [
    {
      "origin": "https://www.instagram.com",
      "localStorage": [
        {
          "name": "example_key",
          "value": "{\"user\":\"example\"}"
        }
      ]
    }
  ]
}
```

Les fichiers de session ne doivent pas être publiés ni partagés. Ils peuvent contenir des informations permettant d'accéder aux comptes utilisés pour la collecte.

### 3.2. Récolte des URLs

Le module `harvester.py` recherche des publications à partir de hashtags :

- `harvest_instagram(hashtag, limit)` collecte des URLs Instagram ;
- `harvest_facebook(hashtag, limit)` collecte des URLs Facebook.

Le module `profile_harvester.py` recherche les publications récentes d'un profil :

- `harvest_instagram_profile(profile_url_or_username, limit)` ;
- `harvest_facebook_profile(profile_url_or_slug, limit)`.

Ces fonctions sont asynchrones et sont appelées avec `asyncio`.

### 3.3. Enrichissement des publications

Une fois les URLs récupérées, elles sont dédoublonnées puis enrichies.

Pour Instagram, `enricher_insta.py` utilise Instaloader afin de récupérer les informations d'une publication et de télécharger les images disponibles. Les données sont sauvegardées dans un fichier `info_post.json`.

Pour Facebook, `enricher_fb.py` utilise Playwright afin d'ouvrir les pages, d'identifier le lien canonique de la publication, d'extraire les métadonnées et de télécharger les images.

Par soucis de performance la partie dédiée au téléchargement des images a été supprimée toutefois ses fonctions ont gardé leurs noms et demeurent dans le projet car elles incluent des processus annexes  nécessaires pour la suite du traitement toutefois on peut les retrouver dans leur intégralité sur le dépôt https://github.com/Lindon1706/projet_stagev2

Les fonctions principales sont :

- `enrich_instagram_batch(...)` : extrait les données d'une liste d'urls de publications instagram ;
- `enrich_facebook_batch(...)` : extrait les données d'une liste d'urls de publications facebook ;
- `process_instagram_post_url(...)` ;
- `process_facebook_photo_url(...)` ;
- `extract_post_metadata(page)`.

### 3.4. Stockage des données

Le module `storage.py` centralise la sauvegarde des données :

- `save_post_data(...)` écrit les métadonnées dans `info_post.json` ;
- `download_image_from_page(...)` télécharge une image depuis une page Facebook ;
- `convert_to_csv(...)` transforme les fichiers JSON d'un dossier en DataFrame puis en CSV ;
- `summarize_data(...)` rassemble les données Facebook et Instagram ;
- `concat_account_info(...)` charge les informations de profils au format JSONL.

Les dossiers de sortie sont organisés par compte ou campagne, avec des sous-dossiers `posts_instagram` et `posts_facebook`.

### 3.5. Consolidation des publications Instagram

Le module `recap_instagram_posts.py` permet de rassembler les publications Instagram de plusieurs comptes dans un seul fichier CSV.

La fonction `compile_instagram_posts_to_csv(...)` extrait notamment :

- le compte auteur ;
- l'URL canonique ;
- la date et l'heure ;
- le texte de la publication ;
- le nombre de photos ;
- les chemins des fichiers image ;
- le dossier d'origine.

Le résultat est généralement enregistré dans `data/Save_csv/recap_instagram.csv`.

## 4. Campagne de collecte

Le script `collecte.py` illustre une campagne complète avec la fonction `run_ritrieval_campaign(...)`.

La campagne suit les étapes suivantes :

1. récupération des publications récentes de profils officiels ;
2. recherche de publications par hashtags ;
3. fusion et dédoublonnage des URLs ;
4. enrichissement des publications Instagram et Facebook ;
5. sauvegarde d'un récapitulatif JSON de la campagne.

Les limites de collecte sont configurables séparément pour les profils et les hashtags. Le nom de la campagne détermine le dossier de sortie dans `data/extracted_posts/`.

## 5. Traitement par intelligence artificielle

### 5.1. Évaluation de la pertinence

La fonction `evaluate_post(...)` du module `AI_treatment.py` envoie les publications à Gemini par lots. Elle ajoute au DataFrame deux colonnes :

- `pertinence` : indique si la publication peut être utile pour un marché de prédiction ;
- `raison` : explique la décision du modèle.

Le traitement est effectué par lots afin de limiter la taille des requêtes. Plusieurs tentatives sont prévues en cas d'erreur temporaire.

### 5.2. Extraction des événements

La fonction `extract_events(...)` analyse les publications jugées pertinentes et demande au modèle de produire des événements exploitables pour des marchés de prédiction.

Chaque événement peut notamment contenir :

- un nom ;
- une catégorie ;
- une date prévue ;
- une description ;
- les identifiants des publications sources.

### 5.3. Génération des marchés

La fonction `generate_markets(...)` transforme les événements en marchés structurés. Le contexte peut inclure le contenu des publications sources ainsi que les marchés déjà produits, afin de réduire les doublons.

Le script `main.py` montre également un appel direct à Gemini à partir du fichier `data/Save_csv/recap_instagram.csv`. La réponse est enregistrée dans un fichier texte et peut aussi être sauvegardée dans un fichier JSON selon le traitement utilisé.

## 6. Calcul des probabilités

Le module `market_probability.py` complète les marchés avec une estimation de probabilité.

### 6.1. Indice d'influence

La fonction `compute_full_data(...)` associe les publications aux informations de leurs auteurs et calcule un indice d'influence à partir de :

- nombre d'abonnés ;
- nombre d'abonnements ;
- vérification du compte ;
- présence d'une biographie ;
- présence de liens externes.

La portée de base est calculée avec une puissance contrôlée par le paramètre `gamma` et de manière logarithmique pour empêcher les très gros compte de biaiser les résultats, puis ajustée par des multiplicateurs de sélectivité et d'autorité.

### 6.2. Estimation et normalisation

La fonction `generate_market_probabilities(...)` transmet à Gemini les informations de l'événement, du marché et des publications sources. Le modèle renvoie une probabilité pour chaque issue.

La fonction `normalize_outcomes_probabilities(...)` :

- convertit les pourcentages en valeurs comprises entre 0 et 1 ;
- ajoute une valeur par défaut pour une issue absente ;
- conserve uniquement les issues attendues ;
- normalise les valeurs pour obtenir une somme égale à 1.

En cas d'échec répété du service, une distribution équiprobable est utilisée comme solution de repli. Cette valeur de repli doit être considérée comme une indication technique et non comme une analyse fiable.

## 7. Données produites

Les principaux formats utilisés sont :

- JSON : métadonnées d'une publication ou résultat d'une campagne ;
- JSONL : informations agrégées sur les profils ;
- CSV : publications consolidées et données prêtes à analyser ;
- TXT ou JSON : réponses et marchés générés par le modèle.

Les sorties existantes se trouvent principalement dans `data/extracted_posts/`, `data/info_save/` et `data/Save_csv/`.

## 8. Dépendances principales

Les bibliothèques externes utilisées sont listées dans  `requirements.txt`. Elles comprennent notamment :

- Playwright pour l'automatisation des navigateurs ;
- Instaloader pour l'accès aux publications Instagram ;
- Pandas et NumPy pour le traitement des données ;
- Pydantic pour la validation des réponses structurées ;
- Google GenAI pour les traitements Gemini ;
- Requests et BeautifulSoup pour certaines recherches web ;
- python-dotenv pour le chargement de variables d'environnement ;
- DDGS pour la recherche sur le web.

## 9. Limites 

- Les plateformes sociales peuvent modifier leur interface ou limiter les requêtes automatisées.
- La collecte peut nécessiter une session authentifiée et dépend de la validité des fichiers de session.
- Les données extraites des publications peuvent être incomplètes ou mal formatées.
- Les résultats de Gemini dépendent de la qualité du texte collecté et du modèle utilisé.
- Une probabilité générée par le modèle dépend de l'influence des auteurs et pas d'un critère plus objectif.
- Les clés d'accès, cookies et fichiers de session peuvent être personnels et ne sont évidement pas fournis.
- Les chemins relatifs utilisés par plusieurs scripts supposent que les commandes sont lancées depuis la racine du projet.
-Les modules d'extraction ont besoin qu'on leur fournisse de vrais comptes à analyser et sont incapables d'obtenir des comptes par d'autres moyens

## 10. État actuel

Le projet fournit les briques principales d'un pipeline de collecte et d'analyse. La collecte Facebook et Instagram, la sauvegarde des publications, la consolidation CSV, l'extraction d'événements et l'estimation de probabilités sont implémentées dans le respect de l'architecture hexagonale.

Il ne fournit pas de système de vérificatio des issues et est seulement capable de générer des marchers et des probabilités


