import asyncio
from pathlib import Path
from modules.enricher import enrich_facebook_batch

# URLs de test (vous pouvez remplacer ou ajouter d'autres URLs de photos Facebook)
TEST_URLS = [
    "https://www.facebook.com/photo/?fbid=122162437718924408",
]

STATE_PATH = Path("config/state_facebook.json")


async def main():
    print("==================================================")
    print("  TEST COMPLET : ENRICHISSEMENT & STOCKAGE FB")
    print("==================================================")

    if not STATE_PATH.exists():
        print(f"❌ Session introuvable : '{STATE_PATH}'. Exécutez d'abord 1_setup_sessions.py.")
        return

    print(f"\n🚀 Démarrage du traitement sur {len(TEST_URLS)} URL(s)...")

    # Appel de l'enrichisseur par batch
    permalinks = await enrich_facebook_batch(TEST_URLS, state_path=STATE_PATH)

    print("\n==================================================")
    print("  RÉSULTAT DE L'EXÉCUTION")
    print("==================================================")
    print(f"✅ Nombre d'URLs traitées : {len(permalinks)}")

    unique_permalinks = set(permalinks)
    print(f"📌 Permaliens uniques générés ({len(unique_permalinks)}) :")
    for pl in unique_permalinks:
        print(f"   • {pl}")

    print("\n📁 Vérifiez le dossier 'data/posts_facebook/' pour consulter les sous-dossiers et fichiers créés !")


if __name__ == "__main__":
    asyncio.run(main())