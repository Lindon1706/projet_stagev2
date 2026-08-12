import asyncio
from pathlib import Path

from modules.harvester import harvest_instagram
from modules.enricher_insta import enrich_instagram_batch

# Nom d'utilisateur Instagram configuré avec la session Instaloader
INSTA_USERNAME = "dimi.tri6687"

# URLs de test manuelles (à utiliser si tu souhaites tester sans passer par le harvester)
MANUAL_TEST_URLS = [
    "https://www.instagram.com/p/DbkhZJzjR2E/"
]


async def run_instagram_test():
    print("==================================================")
    print("  TEST DU PIPELINE INSTAGRAM (HARVESTER + ENRICHER)")
    print("==================================================")

    urls_to_process = []

    # --- ÉTAPE 1 : HARVESTING (Récolte via Hashtag) ---
    hashtag = "tayc"
    limit = 0
    print(f"\n🌾 1. Récolte d'URLs pour #{hashtag} (limit={limit})...")

    try:
        harvested_urls = await harvest_instagram(hashtag=hashtag, limit=limit)
        urls_to_process.extend(harvested_urls)
    except Exception as e:
        print(f"  ⚠️ Erreur lors du harvesting Instagram : {e}")

    # Fallback sur les URLs manuelles si le harvester ne retourne rien ou pour compléter
    if not urls_to_process and MANUAL_TEST_URLS:
        print("  ℹ️ Utilisation des URLs manuelles de fallback.")
        urls_to_process = MANUAL_TEST_URLS

    if not urls_to_process:
        print("\n❌ Aucune URL trouvée à traiter. Ajoute des URLs dans MANUAL_TEST_URLS si besoin.")
        return

    # --- ÉTAPE 2 : ENRICHISSEMENT ---
    print(f"\n🚀 2. Lancement de l'enrichissement sur {len(urls_to_process)} publication(s)...")

    # Appel synchrone d'Instaloader avec le compte connecté
    permalinks = enrich_instagram_batch(
        urls=urls_to_process,
        username=INSTA_USERNAME
    )

    # --- RÉSULTATS ---
    print("\n==================================================")
    print("  RÉSULTATS DE L'EXÉCUTION INSTAGRAM")
    print("==================================================")
    print(f"✅ Publications traitées avec succès : {len(permalinks)}/{len(urls_to_process)}")
    for pl in permalinks:
        print(f"   • {pl}")

    print("\n📁 Vérifie le dossier 'data/posts_instagram/' pour consulter les métadonnées et images téléchargées !")


if __name__ == "__main__":
    asyncio.run(run_instagram_test())