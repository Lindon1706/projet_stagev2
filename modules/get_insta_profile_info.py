import asyncio
import json
import os
import random
import re
import time
import unicodedata
import urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright


def resolve_path(file_path: str) -> Path:
    path_str = str(file_path).strip()
    if "home/" in path_str and not path_str.startswith("/home"):
        path_str = "/" + path_str[path_str.find("home/"):]

    path = Path(path_str)
    if path.is_absolute():
        return path

    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path

    script_dir = Path(__file__).resolve().parent
    script_path = script_dir / path
    if script_path.exists():
        return script_path

    root_path = script_dir.parent / path
    if root_path.exists():
        return root_path

    return cwd_path


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'[\xa0\u00a0\u200b\u202f\u200e\u200f\uFEFF]', ' ', text)
    normalized = unicodedata.normalize('NFKC', text)
    return re.sub(r'\s+', ' ', normalized).strip()


def clean_url(url: str) -> str:
    if not url:
        return None
    if "l.instagram.com" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            if "u" in query:
                url = query["u"][0]
        except Exception:
            pass
    return url.split('?fbclid=')[0].split('&fbclid=')[0]


def parse_stats(raw_stats_text: str) -> dict:
    text = clean_text(raw_stats_text)
    posts_match = re.search(r'([\d.,\s]+[kKmMbB]?)\s+(?:publications|posts)', text, re.IGNORECASE)
    followers_match = re.search(r'([\d.,\s]+[kKmMbB]?)\s+(?:abonnés|followers)', text, re.IGNORECASE)
    following_match = re.search(r'([\d.,\s]+[kKmMbB]?)\s+(?:abonnements|following|suivi\(e\)s)', text, re.IGNORECASE)

    return {
        "posts": clean_text(posts_match.group(1)) if posts_match else None,
        "followers": clean_text(followers_match.group(1)) if followers_match else None,
        "following": clean_text(following_match.group(1)) if following_match else None
    }


def parse_profile_text(header_lines: list, username: str):
    ignore_keywords = [
        'suivre', 'follow', 'contacter', 'contact', 'message',
        's’abonner', 'abonné(e)', 'publications', 'posts',
        'followers', 'abonnés', 'suivi(e)s', 'following', 'plus'
    ]
    clean_lines = []
    for line in header_lines:
        line_str = clean_text(line)
        if not line_str:
            continue
        lower_line = line_str.lower()
        if lower_line.startswith(username.lower()) or any(kw == lower_line for kw in ignore_keywords):
            continue
        if any(kw in lower_line for kw in ['publications', 'followers', 'abonnés', 'suivi(e)s']):
            continue
        if lower_line.startswith('@') or lower_line.endswith(username.lower()):
            continue
        clean_lines.append(line_str)

    full_name = clean_lines[0] if clean_lines else username
    bio_lines = clean_lines[1:] if len(clean_lines) > 1 else []
    final_bio = [l for l in bio_lines if not ('youtube.com' in l or 'http' in l or '.com' in l)]

    return full_name, "\n".join(final_bio)


async def scrape_profile_with_retry(username: str, cookies_path: Path, max_retries: int = 2) -> dict:
    for attempt in range(1, max_retries + 1):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                storage_state=str(cookies_path),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="fr-FR",
                viewport={"width": 1280, "height": 900}
            )
            page = await context.new_page()

            try:
                await page.goto(f"https://www.instagram.com/{username}/", wait_until="domcontentloaded", timeout=30000)

                current_url = page.url
                if "login" in current_url or "challenge" in current_url:
                    print(f"  ⚠️ Redirection détectée (Session expirée ou Challenge). Essai {attempt}/{max_retries}")
                    await browser.close()
                    await asyncio.sleep(random.uniform(5, 8))
                    continue

                await page.wait_for_selector("header", timeout=20000)
                await page.wait_for_timeout(2500)

                data = await page.evaluate("""
                                     () => {
                                         const header = document.querySelector('header');
                                         if (!header) return null;

                                         const isVerified = Boolean(
                                             header.querySelector('svg[aria-label*="Vérifié"], svg[aria-label*="Verified"], svg[title*="Vérifié"], svg[title*="Verified"]')
                                         );

                                         const links = Array.from(header.querySelectorAll('a'));
                                         const rawLinks = [];
                                         for (const a of links) {
                                             if (a.href.includes('l.instagram.com') || (a.href.startsWith('http') && !a.href.includes('instagram.com'))) {
                                                 if (!rawLinks.includes(a.href)) rawLinks.push(a.href);
                                             }
                                         }

                                         return {
                                             isVerified,
                                             rawLinks,
                                             lines: header.innerText.split('\\n')
                                         };
                                     }
                                     """)

                if data and data.get("lines"):
                    header_lines = data.get("lines", [])
                    full_name, bio = parse_profile_text(header_lines, username)
                    raw_links = data.get("rawLinks", [])
                    cleaned_links = list(dict.fromkeys([clean_url(link) for link in raw_links if clean_url(link)]))

                    await browser.close()
                    return {
                        "username": username,
                        "fullName": full_name,
                        "isVerified": data.get("isVerified", False),
                        "bio": bio,
                        "externalLinks": cleaned_links,
                        "stats": parse_stats(" ".join(header_lines))
                    }

            except Exception as e:
                print(f"  ⚠️ Essai {attempt}/{max_retries} échoué pour @{username} : {e}")

            finally:
                try:
                    await browser.close()
                except Exception:
                    pass

        if attempt < max_retries:
            await asyncio.sleep(random.uniform(4, 7))

    return None


async def run_batch_scraping(
        targets_file: str,
        cookies_file: str,
        output_jsonl: str,
        limit: int = None
):
    targets_path = resolve_path(targets_file)
    cookies_path = resolve_path(cookies_file)
    out_jsonl_path = resolve_path(output_jsonl)

    if not targets_path.exists():
        print(f"❌ Fichier targets introuvable : {targets_path.absolute()}")
        return

    if not cookies_path.exists():
        print(f"❌ Fichier cookies introuvable : {cookies_path.absolute()}")
        return

    out_jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    with open(targets_path, "r", encoding="utf-8") as f:
        targets = [line.strip() for line in f if line.strip()]

    processed = set()
    if out_jsonl_path.exists():
        with open(out_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        processed.add(data.get("username", "").lower())
                    except json.JSONDecodeError:
                        continue

    to_scrape = [u for u in targets if u.lower() not in processed]
    if limit is not None and limit > 0:
        to_scrape = to_scrape[:limit]

    print(f"📊 Total : {len(targets)} | Déjà faits : {len(processed)} | ⏳ À scraper : {len(to_scrape)}\n")

    if not to_scrape:
        print("✅ Aucun nouveau profil à scraper.")
        return

    for index, username in enumerate(to_scrape, 1):
        print(f"[{index}/{len(to_scrape)}] Scrape de @{username}...")

        result = await scrape_profile_with_retry(username=username, cookies_path=cookies_path, max_retries=2)

        if result:
            with open(out_jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(f"  ✅ Récupéré")
        else:
            print(f"  ❌ Échec définitif (Profil privé, introuvable ou blocage)")

        if index < len(to_scrape):
            pause = random.uniform(4.0, 8.0)
            await asyncio.sleep(pause)


if __name__ == "__main__":
    asyncio.run(run_batch_scraping(
        targets_file="data/info_save/fail.txt",
        cookies_file="config/state_instagram.json",
        output_jsonl="data/info_save/all_profiles.jsonl",
        limit=204
    ))