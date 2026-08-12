import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
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


async def harvest_instagram(hashtag: str, limit: int = 10) -> list[str]:
    if not IG_STATE_PATH.exists():
        raise FileNotFoundError(
            f"❌ Fichier de session introuvable : '{IG_STATE_PATH}'."
        )

    clean_hashtag = hashtag.lstrip("#")
    url = f"https://www.instagram.com/explore/tags/{clean_hashtag}/"
    urls = set()

    print(
        f"🔍 [Harvester IG] Recherche de #{clean_hashtag} (objectif: {limit} URLs)..."
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=IG_STATE_PATH, user_agent=USER_AGENT
        )
        page = await context.new_page()

        await page.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2}",
            lambda route: route.abort(),
        )

        try:
            await page.goto(url, wait_until="commit", timeout=60000)
            await page.wait_for_timeout(3000)

            for scroll_step in range(10):
                links = await page.eval_on_selector_all(
                    "a", "elements => elements.map(e => e.href)"
                )

                for link in links:
                    if "/p/" in link or "/reel/" in link:
                        urls.add(link.split("?")[0])

                print(
                    f"   └─ Scroll {scroll_step + 1} : {len(urls)}/{limit} URLs trouvées"
                )
                if len(urls) >= limit:
                    break

                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(2500)

        except Exception as e:
            print(f"⚠️ Avertissement lors de la récolte Instagram : {e}")
        finally:
            await browser.close()

    result_list = list(urls)[:limit]
    print(
        f"✅ [Harvester IG] Récolte terminée : {len(result_list)} URLs obtenues."
    )
    return result_list


async def harvest_facebook(hashtag: str, limit: int = 10) -> list[str]:
    if not FB_STATE_PATH.exists():
        raise FileNotFoundError(
            f"❌ Fichier de session introuvable : '{FB_STATE_PATH}'."
        )

    clean_hashtag = hashtag.lstrip("#")
    url = f"https://www.facebook.com/hashtag/{clean_hashtag}"
    urls = set()

    print(
        f"🔍 [Harvester FB] Recherche de #{clean_hashtag} (objectif: {limit} URLs)..."
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=FB_STATE_PATH, user_agent=USER_AGENT
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
                    timeout=12000,
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
                "/reel/",
            ]

            for scroll_step in range(10):
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
            print(f"⚠️ Avertissement lors de la récolte Facebook : {e}")
        finally:
            await browser.close()

    result_list = list(urls)[:limit]
    print(
        f"✅ [Harvester FB] Récolte terminée : {len(result_list)} URLs obtenues."
    )
    return result_list


if __name__ == "__main__":

    async def _test():
        print("\n--- TEST HARVESTER FACEBOOK ---")
        fb_links = await harvest_facebook("Tayc", limit=2)
        for u in fb_links:
            print(" •", u)

    asyncio.run(_test())