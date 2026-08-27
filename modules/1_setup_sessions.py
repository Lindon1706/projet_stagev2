import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Chemins de sauvegarde dans le dossier config/
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_DIR.mkdir(exist_ok=True,parents=True)
IG_STATE_PATH = CONFIG_DIR / "state_instagram.json"
FB_STATE_PATH = CONFIG_DIR / "state_facebook.json"


async def setup_platform_session(platform_name, login_url, output_path):
    """Ouvre un navigateur interactif, attend la connexion manuelle

    et sauvegarde l'état de la session (cookies & localStorage).
    """
    print("\n" + "=" * 55)
    print(f"🌐 INITIALISATION DE LA SESSION : {platform_name.upper()}")
    print("=" * 55)

    # Création automatique du dossier config/ si absent
    CONFIG_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        # Lancement en mode visible (headless=False) avec fenêtre agrandie
        browser = await p.chromium.launch(
            headless=False, args=["--start-maximized"]
        )

        context = await browser.new_context(
            no_viewport=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        print(f"-> Navigation vers {login_url}...")
        await page.goto(login_url)

        print(
            f"\n👉 [ACTION REQUISE] Connecte-toi à ton compte {platform_name}."
        )
        print(
            "   Prends ton temps pour valider la double authentification (2FA) si demandée."
        )

        # Met le script en pause le temps que l'utilisateur se connecte dans le navigateur
        input(
            f"\n Appuie sur [ENTRÉE] dans ce terminal une fois connecté sur {platform_name}..."
        )

        # Enregistrement de la session
        await context.storage_state(path=output_path)
        print(
            f" SUCCESS : Session {platform_name} sauvegardée sous '{output_path}' !"
        )

        await browser.close()


async def main():
    print("🚀 Démarrage de la configuration des sessions...")

    # 1. Session Instagram
    await setup_platform_session(
        platform_name="Instagram",
        login_url="https://www.instagram.com/",
        output_path=IG_STATE_PATH,
    )

    # 2. Session Facebook
    await setup_platform_session(
        platform_name="Facebook",
        login_url="https://www.facebook.com/",
        output_path=FB_STATE_PATH,
    )

    print("\n" + "=" * 55)
    print(" TOUTES LES SESSIONS ONT ÉTÉ ENREGISTRÉES !")
    print(f"   • Instagram : {IG_STATE_PATH}")
    print(f"   • Facebook  : {FB_STATE_PATH}")
    print(
        "Les modules de scraping pourront désormais utiliser ces fichiers en mode invisible."
    )
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())