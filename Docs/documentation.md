# Documentation du projet

## 1. Présentation

Ce projet collecte des publications Facebook et Instagram au sujet d'artistes, de médias et d'événements culturels africains. Les données collectées sont enrichies, consolidées, analysées par Gemini, puis utilisées pour extraire des événements et générer des marchés de prédiction avec des probabilités estimées.

Le pipeline comprend :

1. la collecte d'URLs depuis des profils et des hashtags ;
2. l'enrichissement des publications ;
3. la sauvegarde des métadonnées et la consolidation en CSV ;
4. l'évaluation des publications par Gemini ;
5. l'extraction d'événements et la génération de marchés ;
6. l'estimation et la normalisation des probabilités.

La collecte et l'enrichissement Facebook utilisent Playwright asynchrone. L'enrichissement Instagram utilise Instaloader. Les traitements Gemini et pandas sont exécutés de manière synchrone.

## 2. Organisation du projet

- `config/` : fichiers de session Playwright pour Facebook et Instagram.
- `contexts/` : contextes textuels utilisés par certains traitements.
- `data/` : publications, profils et résultats générés.
- `Docs/` : documentation et schéma de fonctionnement.
- `modules/` : modules de collecte, d'enrichissement, de stockage et d'analyse.
- `collecte.py` : lance une campagne de collecte complète.
- `main.py` : lance le traitement IA et le calcul des probabilités sur les données collectées.
- `requirements.txt` : dépendances Python du projet.
- `test.ipynb` : notebook d'essais et d'exploration.

## 3. Préparation

Installer les dépendances :

```bash
pip install -r requirements.txt
playwright install
```

Créer un fichier `.env` à la racine du projet et définir la clé Gemini :

```env
GEMINI_API_KEY="votre_cle_api"
```

La variable `GEMINI_MODEL` peut être définie pour choisir un modèle différent. À défaut, les modules utilisent la valeur configurée dans le code.

## 4. Sessions Playwright

Le module `modules/1_setup_sessions.py` permet de créer des sessions réutilisables dans `config/`. Les fichiers `state_facebook.json` et `state_instagram.json` sont des Storage States Playwright. Ils peuvent contenir des cookies et des données `localStorage` permettant d'accéder à un compte.

Exemple anonymisé de structure :

```json
{
  "cookies": [
    {
      "name": "nom_du_cookie",
      "value": "valeur_exemple",
      "domain": ".example.com",
      "path": "/",
      "expires": 0,
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    }
  ],
  "origins": [
    {
      "origin": "https://www.example.com",
      "localStorage": [
        {
          "name": "cle_exemple",
          "value": "valeur_exemple"
        }
      ]
    }
  ]
}
```

Les fichiers de session ne doivent jamais être publiés, commités ou partagés. Ils doivent rester locaux et être renouvelés lorsqu'une session expire.

## 5. Collecte et enrichissement

Les fonctions de `modules/harvester.py` recherchent des URLs depuis des hashtags. Les fonctions de `modules/profile_harvester.py` recherchent les publications récentes d'un profil. Ces fonctions sont asynchrones et doivent être appelées avec `await` dans une boucle asyncio.

`collecte.py` orchestre les étapes suivantes :

1. collecte depuis les profils officiels ;
2. collecte depuis les hashtags ;
3. dédoublonnage des URLs ;
4. enrichissement Instagram et Facebook ;
5. sauvegarde des résultats dans `data/extracted_posts/`.

Pour Instagram, `modules/enricher_insta.py` utilise Instaloader. Pour Facebook, `modules/enricher_fb.py` utilise Playwright asynchrone. Les métadonnées sont généralement sauvegardées dans un fichier `info_post.json` par publication.

## 6. Stockage et consolidation

`modules/storage.py` fournit notamment les fonctions de sauvegarde, de conversion JSON vers CSV et de consolidation des informations de profils. `modules/recap_instagram_posts.py` regroupe les publications Instagram dans un CSV, par exemple `data/Save_csv/recap_instagram.csv`.

`modules/get_insta_profile_info.py` collecte les informations de profils Instagram et les écrit au format JSONL, par exemple dans `data/info_save/all_profiles.jsonl`. Ce module utilise également exclusivement Playwright asynchrone.

## 7. Traitement IA

`main.py` charge les fichiers `info_post.json` sous `data/extracted_posts/`, puis exécute :

1. `evaluate_post(...)` pour marquer les publications pertinentes ;
2. `extract_events(...)` pour extraire les événements ;
3. `generate_markets(...)` pour générer jusqu'à trois marchés par événement ;
4. `process_events_and_add_probabilities(...)` pour calculer les probabilités.

Les sorties principales sont enregistrées dans `data/Save_csv/`. Les réponses structurées sont validées avec Pydantic avant leur sauvegarde.

## 8. Calcul des probabilités

`modules/market_probability.py` calcule un indice d'influence à partir des informations de profils : abonnés, abonnements, vérification, biographie et liens externes. Il associe ensuite cet indice aux publications et le transmet au modèle Gemini avec les données de l'événement et du marché.

Les probabilités sont converties entre pourcentages et valeurs décimales, limitées à une plage raisonnable, filtrées sur les issues attendues puis normalisées afin que leur somme soit égale à 1. En cas d'échec répété de Gemini, une distribution équiprobable est produite. Cette distribution est un fallback technique et ne constitue pas une estimation fondée sur de nouvelles données.

## 9. Formats de sortie

- JSON : métadonnées, événements et marchés.
- JSONL : profils agrégés, une entrée par ligne.
- CSV : publications consolidées et données préparées pour l'analyse.
- TXT : certaines réponses ou sorties intermédiaires.

Les sorties existantes se trouvent principalement dans `data/extracted_posts/`, `data/info_save/` et `data/Save_csv/`.

## 10. Limites et précautions

- Instagram et Facebook peuvent modifier leur interface, limiter les requêtes ou expirer les sessions.
- Les chemins relatifs supposent généralement que les commandes sont lancées depuis la racine du projet.
- Les données extraites peuvent être incomplètes ou mal formatées.
- Les traitements Gemini nécessitent une clé API et dépendent de la qualité des données transmises.
- Les probabilités produites sont des estimations de modèle, pas des vérités ni des garanties.
- Le projet génère des marchés et des probabilités, mais ne fournit pas de système automatique de vérification des résultats ni de règlement des issues.
- Les comptes et profils à analyser doivent être fournis dans la configuration de la campagne ; le projet ne découvre pas automatiquement des comptes à partir d'une source externe.
- Les clés API, cookies, Storage States et données personnelles doivent rester hors du dépôt public.

## 11. Vérification locale

Une vérification syntaxique peut être lancée avec :

```bash
python -m compileall main.py collecte.py modules
```

Cette commande vérifie la syntaxe Python, mais ne remplace pas un test réel de collecte, d'authentification ou d'appel Gemini.
