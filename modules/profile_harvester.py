import asyncio
from pathlib import Path
from typing import List
from playwright.async_api import async_playwright

from modules.utils import clean_facebook_url

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
IG_STATE_PATH = CONFIG_DIR / "state_instagram.json"
FB_STATE_PATH = CONFIG_DIR / "state_facebook.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def harvest_instagram_profile(
        profile_url_or_username: str,
        limit: int = 10
) -> List[str]:
    """
    Récolte les URLs des publications depuis un profil Instagram via Playwright.
    Capture ligne par ligne (pas de 350px) en conservant l'ordre exact du profil.
    """
    if not IG_STATE_PATH.exists():
        raise FileNotFoundError(f"❌ Fichier de session introuvable : '{IG_STATE_PATH}'.")

    if not profile_url_or_username.startswith("http"):
        clean_user = profile_url_or_username.lstrip("@").strip("/")
        url = f"https://www.instagram.com/{clean_user}/"
    else:
        url = profile_url_or_username.rstrip("/") + "/"

    # Utilisation d'une liste ordonnée + ensemble de contrôle pour préserver l'ordre
    collected_urls = []
    seen_urls = set()

    print(f"\n🔍 [Profile Harvester IG] Consultation du profil : {url} (objectif: {limit} URLs)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=IG_STATE_PATH,
            user_agent=USER_AGENT
        )
        page = await context.new_page()

        await page.route("**/*.{woff,woff2,ttf,otf}", lambda route: route.abort())

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # 1. Alignement strict tout en haut du profil
            await page.evaluate("window.scrollTo(0, 0)")

            # 2. Attente explicite de l'hydratation du DOM de la grille
            try:
                await page.wait_for_selector('main a[href*="/p/"], main a[href*="/reel/"]', timeout=15000)
            except Exception:
                pass

            await page.wait_for_timeout(3000)

            # Fonction d'extraction ligne par ligne
            async def _extract_visible_links():
                links = await page.eval_on_selector_all(
                    "a", "elements => elements.map(e => e.href)"
                )
                for link in links:
                    if "/p/" in link or "/reel/" in link:
                        clean = link.split("?")[0]
                        if clean not in seen_urls:
                            seen_urls.add(clean)
                            collected_urls.append(clean)

            # Capture initiale du premier rang et des posts épinglés
            await _extract_visible_links()
            print(f"   └─ Capture initiale (haut de page) : {len(collected_urls)}/{limit} URLs trouvées")

            # 3. Défilement ligne par ligne (350px = ~1 ligne)
            scroll_attempts = 0
            max_scrolls = 30

            while len(collected_urls) < limit and scroll_attempts < max_scrolls:
                await page.mouse.wheel(0, 350)
                await page.wait_for_timeout(1500)

                await _extract_visible_links()
                scroll_attempts += 1

                print(f"   └─ Micro-scroll {scroll_attempts} : {len(collected_urls)}/{limit} URLs trouvées")

        except Exception as e:
            print(f"⚠️ Avertissement lors de la récolte du profil Instagram : {e}")
        finally:
            await browser.close()

    result_list = collected_urls[:limit]
    print(f"✅ [Profile Harvester IG] Récolte terminée : {len(result_list)} URLs obtenues.")
    return result_list


async def harvest_facebook_profile(
        profile_url_or_slug: str,
        limit: int = 10
) -> List[str]:
    """
    Récolte les URLs des publications d'un profil/page Facebook via Playwright.
    """
    if not FB_STATE_PATH.exists():
        raise FileNotFoundError(f"❌ Fichier de session introuvable : '{FB_STATE_PATH}'.")

    if not profile_url_or_slug.startswith("http"):
        clean_slug = profile_url_or_slug.strip("/")
        url = f"https://www.facebook.com/{clean_slug}"
    else:
        url = profile_url_or_slug

    urls = set()
    print(f"\n🔍 [Profile Harvester FB] Récupération du profil : {url} (objectif: {limit} URLs)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=FB_STATE_PATH,
            user_agent=USER_AGENT
        )
        page = await context.new_page()

        await page.route(
            "**/*.{png,jpg,jpeg,gif,woff,woff2}", lambda route: route.abort()
        )

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            try:
                await page.wait_for_selector(
                    'div[role="feed"], div[role="article"], a[href*="facebook.com"]',
                    timeout=12000
                )
            except Exception:
                pass

            await page.wait_for_timeout(3000)

            target_keywords = [
                "/posts/",
                "pfbid",
                "/videos/",
                "permalink.php",
                "/photo",
                "story_fbid",
                "fbid=",
                "/reel/"
            ]

            for scroll_step in range(12):
                articles = await page.query_selector_all('div[role="article"]')

                if articles:
                    for article in articles:
                        article_links = await article.eval_on_selector_all(
                            "a", "els => els.map(e => e.href)"
                        )
                        for link in article_links:
                            if any(k in link for k in target_keywords):
                                clean_link = clean_facebook_url(link)
                                if clean_link:
                                    urls.add(clean_link)
                else:
                    links = await page.eval_on_selector_all(
                        "a", "elements => elements.map(e => e.href)"
                    )
                    for link in links:
                        if any(k in link for k in target_keywords):
                            clean_link = clean_facebook_url(link)
                            if clean_link:
                                urls.add(clean_link)

                print(
                    f"   └─ Scroll {scroll_step + 1} : {len(urls)}/{limit} URLs trouvées"
                )
                if len(urls) >= limit:
                    break

                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(3000)

        except Exception as e:
            print(f"⚠️ Avertissement lors de la récolte du profil Facebook : {e}")
        finally:
            await browser.close()

    result_list = list(urls)[:limit]
    print(f"✅ [Profile Harvester FB] Récolte terminée : {len(result_list)} URLs obtenues.")
    return result_list


if __name__ == "__main__":
    async def _test():
        print("--- TEST PROFILE HARVESTER (LIGNE PAR LIGNE) ---")
        ig_urls = await harvest_instagram_profile("tayc", limit=9)
        for idx, u in enumerate(ig_urls, 1):
            print(f" {idx}. {u}")


    asyncio.run(_test())