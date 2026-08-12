# 📄 CONTEXTE DU PROJET : Module Facebook (Harvester + Enricher + Storage)

## 📌 Statut du Module
**Étape actuelle :** Module `Enricher` & `Storage` Facebook **Terminé et Validé** ✅  
**Dernière mise à jour :** Août 2026  
**Environnement :** Python 3.10+, Playwright (async), Ubuntu / Windows

---

## 📁 Architecture des Fichiers

```text
projet_stage/
├── config/
│   └── state_facebook.json      # Session Facebook Playwright (cookies / auth)
├── modules/
│   ├── harvester.py             # Récolte des URLs brutes de photos / posts Facebook
│   ├── utils.py                 # Résolution des URLs & permaliens canoniques
│   ├── storage.py               # Gestion du système de fichiers local & téléchargement HD
│   └── enricher.py              # Extraction texte/auteur/date + coordination batch
├── data/
│   └── posts_facebook/          # Stockage local structuré par publication
│       └── post_<ID>/
│           ├── info_post.json   # Métadonnées complètes
│           ├── photo_1.jpg      # Image principale HD
│           └── photo_2.jpg      # Image secondaire (si publication multi-images)
└── main.py                      # Script d'exécution & orchestration du pipeline            # Script d'exécution & orchestration du pipeline