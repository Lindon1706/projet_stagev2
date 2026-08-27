# Infor

## 1. Présentation

Ce projet a pour objectif de collecter des informations publiées en ligne au sujet d'artistes, de médias ou d'événements culturels africains, puis d'utiliser ces données pour identifier des événements et générer des marchés de prédiction.

Le pipeline combine :

1. la collecte de publications Facebook et Instagram ;
2. l'extraction des métadonnées et des images associées ;
3. la consolidation des données dans des fichiers CSV ;
4. l'analyse des publications par un modèle Gemini ;
5. la génération d'événements, de marchés et de probabilités estimées.


## 2. Organisation du projet

- `config/` : fichiers de session utilisés pour l'accès à Facebook et Instagram.
- `contexts/` : éléments de contexte utilisés pour les traitements.
- `data/` : publications collectées, images, métadonnées, profils et résultats générés.
- `info/` : documentation et fichier de dépendances d'origine.
- `modules/` : fonctions principales du projet.
- `main.py` : fichier principal permettant à la racine du projet.
- `collecte.py` : lancement d'une campagne de collecte configurée pour un profil ou un hashtag.
- `1_setup_sessions.py` : préparation de sessions navigateur avec Playwright.


Plus d'informations dans `Docs/documentation.md`
