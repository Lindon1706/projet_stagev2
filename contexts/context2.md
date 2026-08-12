# 📄 CONTEXTE.MD — Projet Scraping Facebook & Instagram

## 📌 1. Vue d'ensemble du projet
Développement d'une application modulaire en **Python** basée sur **Playwright (Async)** pour collecter et enrichir des publications publiques sur **Facebook** et **Instagram** via des hashtags ciblés.

Le pipeline suit la logique suivante :
1. **Sessions** : Utilisation des cookies/états de navigation sauvegardés (`state_facebook.json`, `state_instagram.json`).
2. **Harvester (`modules/harvester.py`)** : Défilement automatique, extraction des liens de publications et nettoyage strict des URLs.
3. **Enricher (`../modules/enricher_fb.py`)** : Visite de chaque URL, dépliage du texte ("Voir plus") et extraction du texte + lien de l'image HD.
4. **Orchestrateur (`main.py`)** : [En cours] Lancement du pipeline complet et export (JSON/CSV).

---

## 📁 2. Structure du projet

```text
projet_scraper/
│
├── config/
│   ├── state_facebook.json      # Session Facebook active
│   └── state_instagram.json     # Session Instagram active
│
├── modules/
│   ├── __init__.py
│   ├── harvester.py             # [VALIDÉ] Récolte & nettoyage des URLs
│   └── enricher.py              # [VALIDÉ] Extraction contenu (texte + images)
│
├── 1_setup_sessions.py          # Script de connexion initiale
├── main.py                      # [À CRÉER] Pipeline principal & export
└── contexte.md                  # Ce fichier