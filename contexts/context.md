# Contexte du Projet : Scraper Facebook & Instagram (#Tayc)

## Objectif
Créer un scraper robuste et modulaire en Python pour récolter et enrichir des publications sur des hashtags Instagram et Facebook.

## Architecture & Stratégie (Pipeline en 2 étapes)
1. **Étape 1 - Harvester (Playwright) :** Navigue en mode headless avec sessions sauvegardées (`config/state_*.json`) et récolte les URLs / shortcodes des publications.
2. **Étape 2 - Enricher (Instaloader) :** Utilise les shortcodes récoltés pour extraire le contenu complet via `Post.from_shortcode()` (légendes, likes, médias HD, dates) de façon très stable sans déclencher d'erreurs d'API.

## Arborescence retenue
- `config/` : Contient `state_instagram.json` et `state_facebook.json` (sessions Playwright).
- `data/` : Reçoit les fichiers d'extraction (JSON/CSV).
- `modules/` :
  - `../modules/harvester.py` (Playwright)
  - `enricher.py` (Instaloader)
- `1_setup_sessions.py` : Script à exécuter une fois pour enregistrer les sessions de connexion.
- `main.py` : Chef d'orchestre.

## État actuel du projet
Arborescence créée, nous sommes prêts à écrire le code des fichiers un par un en commençant par `1_setup_sessions.py`.