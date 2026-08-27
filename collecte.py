import asyncio
import json
import os
from pathlib import Path

# Importer les modules du projet
from modules.profile_harvester import (
    harvest_instagram_profile,
    harvest_facebook_profile,
)
from modules.harvester import (
    harvest_instagram,
    harvest_facebook,
)
from modules.enricher_insta import enrich_instagram_batch
from modules.enricher_fb import enrich_facebook_batch

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" /"extracted_posts"
DATA_DIR.mkdir(exist_ok=True)


async def run_ritrieval_campaign(name: str, insta_profile : str, facebook_profile : str, insta_hashtag : str, facebook_hashtag : str, insta_profile_limit: int, facebook_profile_limit: int, insta_hashtag_limit: int, facebook_hashtag_limit: int) :

    CAMPAIGN_DIR = DATA_DIR / f"{name}"
    CAMPAIGN_DIR.mkdir(exist_ok=True)

    INSTA_DATA_DIR = CAMPAIGN_DIR / "posts_instagram"
    INSTA_DATA_DIR.mkdir(exist_ok=True)
    FB_DATA_DIR = CAMPAIGN_DIR / "posts_facebook"
    FB_DATA_DIR.mkdir(exist_ok=True)

    print("==================================================")
    print(f"🚀 LANCEMENT DE LA CAMPAGNE DE COLLECTE POUR {name.upper()} ")
    print("==================================================")

    # ----------------------------------------------------
    # 1. RÉCOLTE SUR LES PROFILS OFFICIELS
    # ----------------------------------------------------
    print("\n--- 👤 ÉTAPE 1 : Récolte des Profils Officiels ---")

    #derniers posts Instagram Officiel
    ig_profile_urls = []
    if insta_profile and insta_profile_limit:
        print(f"récupération de {insta_profile_limit} publications depuis le compte {insta_profile}")
        ig_profile_urls = await harvest_instagram_profile(
            profile_url_or_username=insta_profile, limit=insta_profile_limit
        )

    # 10 derniers posts Facebook Officiel
    fb_profile_urls = []
    if facebook_profile and facebook_profile_limit:
        print(f"récupération de {facebook_profile_limit} publications depuis le compte {facebook_profile}")
        fb_profile_urls = await harvest_facebook_profile(
            profile_url_or_slug=facebook_profile, limit=facebook_profile_limit
        )

    # ----------------------------------------------------
    # 2. RÉCOLTE DANS LES HASHTAGS & RECHERCHES (COMMUNAUTÉ)
    # ----------------------------------------------------
    print("\n--- 🔍 ÉTAPE 2 : Récolte Communauté & Tournée ---")

    # 30 posts Instagram via Hashtag #tayc
    ig_hashtag_urls = []
    if insta_hashtag and insta_hashtag_limit:
        print(f"récupération de {insta_hashtag_limit} publications depuis le hashtag {insta_hashtag}")
        ig_hashtag_urls = await harvest_instagram(
            hashtag=insta_hashtag, limit=insta_hashtag_limit
        )

    # 30 posts Facebook via Recherche/Hashtag #tayc
    fb_search_urls = []
    if facebook_hashtag and facebook_hashtag_limit:
        print(f"récupération de {facebook_hashtag_limit} publications depuis le hashtag {facebook_hashtag}")
        fb_search_urls = await harvest_facebook(
            hashtag=facebook_hashtag, limit=facebook_hashtag_limit
        )

    # ----------------------------------------------------
    # 3. CONSOLIDATION & DÉDOUBLONNAGE
    # ----------------------------------------------------
    print("\n--- 🧹 ÉTAPE 3 : Dédoublonnage des URLs ---")

    # Fusion des URLs Instagram
    all_ig_urls = []
    if ig_profile_urls or ig_hashtag_urls:
        all_ig_urls = list(dict.fromkeys(ig_profile_urls + ig_hashtag_urls))

    # Fusion des URLs Facebook
    all_fb_urls = []
    if fb_profile_urls or fb_search_urls:
        all_fb_urls = list(dict.fromkeys(fb_profile_urls + fb_search_urls))

    print(f"📊 Totaux uniques retenus :")
    print(f"   ├─ Instagram : {len(all_ig_urls)} URLs")
    print(f"   └─ Facebook  : {len(all_fb_urls)} URLs")

    # ----------------------------------------------------
    # 4. ENRICHISSEMENT DES DONNÉES
    # ----------------------------------------------------
    print("\n--- 💎 ÉTAPE 4 : Enrichissement des Métadonnées ---")

    ig_data = []
    fb_data = []

    if all_ig_urls:
        print(f"\n📸 Enrichissement de {len(all_ig_urls)} posts Instagram...")
        ig_data = enrich_instagram_batch(
            urls=all_ig_urls, username=os.environ.get("USERNAME"),INSTA_DATA_DIR = INSTA_DATA_DIR
        )

    if all_fb_urls:
        print(f"\n📘 Enrichissement de {len(all_fb_urls)} posts Facebook...")
        fb_data = await enrich_facebook_batch(urls=all_fb_urls,FB_DATA_DIR=FB_DATA_DIR)

    # ----------------------------------------------------
    # 5. SAUVEGARDE FINALE
    # ----------------------------------------------------
    output_payload = {
        "metadata": {
            "target": "Tayc",
            "total_ig_posts": len(ig_data),
            "total_fb_posts": len(fb_data),
        },
        "instagram_posts": ig_data,
        "facebook_posts": fb_data,
    }

    output_path = INSTA_DATA_DIR / f"collecte_{name}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=4)

    print("\n==================================================")
    print(f"✅ COLLECTE TERMINÉE AVEC SUCCÈS !")
    print(f"📁 Données sauvegardées dans : {output_path}")
    print("==================================================")

hashtags = ["EastAfricanMusic"," BongoFlava", "Afrobeats", "AfricanRap"]
profiles = ["tayc"]

if __name__ == "__main__":
    for profile in profiles:
        asyncio.run(
            run_ritrieval_campaign(profile,profile,"","tayc","",10,0,10,0)
        )