import asyncio
import json
from pathlib import Path
from playwright.async_api import Page, async_playwright

from modules.utils import get_canonical_permalink
from modules.storage import (
    BASE_DATA_DIR,
    sanitize_folder_name,
    download_image_from_page,
    save_post_data,
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
FB_STATE_PATH = CONFIG_DIR / "state_facebook.json"


async def extract_post_metadata(page: Page) -> dict:
    """
    Extrait le texte déplié, l'auteur et la date depuis la page de publication (permalien).
    """
    metadata = {"author": "", "date": "", "text": ""}

    # 1. Déplier le texte ("Voir plus")
    try:
        see_more = await page.query_selector(
            'div[role="button"]:has-text("Voir plus"), div[role="button"]:has-text("See more")'
        )
        if see_more:
            await see_more.click()
            await page.wait_for_timeout(500)
    except Exception:
        pass

    # 2. Extraction du texte
    try:
        text_selectors = [
            'div[data-ad-preview="message"]',
            'div[data-ad-comet-preview="message"]',
            'div[role="article"] div[dir="auto"]',
            'div[role="main"] div[dir="auto"]',
        ]
        extracted_text = ""
        for selector in text_selectors:
            elements = await page.query_selector_all(selector)
            for el in elements:
                txt = (await el.inner_text()).strip()
                if len(txt) > len(extracted_text):
                    extracted_text = txt

        if not extracted_text:
            meta_desc = await page.query_selector('meta[property="og:description"], meta[name="description"]')
            if meta_desc:
                extracted_text = await meta_desc.get_attribute("content") or ""

        metadata["text"] = extracted_text
    except Exception:
        pass

    # 3. Extraction de l'auteur
    try:
        author_selectors = [
            'h2 strong span',
            'h2 a[role="link"]',
            'h3 a[role="link"]',
            'strong a[role="link"]'
        ]
        ignore_author = ["créer une publication", "create post", "créer un reel"]
        for sel in author_selectors:
            elements = await page.query_selector_all(sel)
            for el in elements:
                txt = (await el.inner_text()).strip()
                if txt and txt.lower() not in ignore_author and len(txt) < 80:
                    metadata["author"] = txt
                    break
            if metadata["author"]:
                break
    except Exception:
        pass

    # 4. Extraction de la date (Ciblage strict par aria-label + nettoyage d'espaces)
    try:
        # Sur FB, les dates du post principal sont dans des liens munis d'un aria-label explicite
        candidate_links = await page.query_selector_all(
            'div[role="main"] a[aria-label], div[role="article"] a[aria-label]'
        )

        date_keywords = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre",
            "janv", "févr", "avr", "juil", "sept", "oct", "nov", "déc",
            "heure", "jour", "min", " à ", "202"
        ]

        for link in candidate_links:
            aria = await link.get_attribute("aria-label") or ""
            # Nettoyage des espaces insécables Facebook sans risque de crash
            clean_aria = aria.replace('\u202f', ' ').replace('\u200e', ' ').replace('\xa0', ' ').strip()

            low_aria = clean_aria.lower()
            # On s'assure que c'est une date et pas un bouton ("J'aime", "Partager"...)
            if any(kw in low_aria for kw in date_keywords) and any(c.isdigit() for c in clean_aria):
                metadata["date"] = clean_aria
                break

        # Fallback si l'aria-label n'a rien donné : texte du lien de permalien
        if not metadata["date"]:
            text_links = await page.query_selector_all('a[href*="permalink.php"], a[href*="/posts/"]')
            for link in text_links:
                txt = await link.inner_text()
                clean_txt = txt.replace('\u202f', ' ').replace('\u200e', ' ').replace('\xa0', ' ').strip()
                if clean_txt and any(c.isdigit() for c in clean_txt) and len(clean_txt) < 30:
                    if clean_txt != metadata.get("author"):
                        metadata["date"] = clean_txt
                        break
    except Exception as e:
        print(f"  ⚠️ Extraction date contournée : {e}")

    return metadata

async def process_facebook_photo_url(page: Page, url: str) -> str:
    """
    Traite une URL photo Facebook :
    1. Récupère son permalien canonique.
    2. Si le dossier existe déjà : télécharge l'image HD et met à jour info_post.json.
    3. Si le dossier n'existe pas : télécharge l'image, crée le dossier,
       visite le permalien pour extraire auteur/date/texte, puis crée info_post.json.
    """
    print(f"\n🔍 [Enricher FB] Traitement de : {url}")

    # Étape A : Visiter la page photo pour extraire le permalien
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(2000)

    canonical_url = await get_canonical_permalink(page)
    folder_name = sanitize_folder_name(canonical_url)
    post_folder = BASE_DATA_DIR / folder_name
    json_path = post_folder / "info_post.json"

    # CAS 1 : Le dossier du permalien EXISTE DÉJÀ
    if json_path.exists():
        print(f"  📂 Dossier existant trouvé : {folder_name}")

        # Calcul du nom de la nouvelle image (photo_2.jpg, photo_3.jpg...)
        existing_photos = list(post_folder.glob("photo_*.jpg"))
        next_num = len(existing_photos) + 1
        photo_filename = f"photo_{next_num}.jpg"
        target_path = post_folder / photo_filename

        # Téléchargement direct depuis la page photo courante
        downloaded = await download_image_from_page(page, target_path)

        if downloaded:
            print(f"  📸 Image secondaire enregistrée : {photo_filename}")

            # Mise à jour du fichier info_post.json
            with open(json_path, "r", encoding="utf-8") as f:
                info_data = json.load(f)

            if photo_filename not in info_data.get("photo_files", []):
                info_data.setdefault("photo_files", []).append(photo_filename)
                info_data["total_photos"] = len(info_data["photo_files"])

            save_post_data(post_folder, info_data)
        else:
            print(f"  ⚠️ Impossible de télécharger l'image pour {url}")

        return canonical_url

    # CAS 2 : Le dossier n'existe PAS ENCORE (Premier passage sur ce post)
    print(f"  🆕 Premier passage. Création du dossier : {folder_name}")
    post_folder.mkdir(parents=True, exist_ok=True)

    # 1. Télécharger la première photo (photo_1.jpg) avant de quitter la page photo
    photo_filename = "photo_1.jpg"
    target_path = post_folder / photo_filename
    downloaded = await download_image_from_page(page, target_path)

    photo_files = [photo_filename] if downloaded else []
    if downloaded:
        print(f"  📸 Première image enregistrée : {photo_filename}")

    # 2. Navigation vers la page du permalien si elle diffère de l'URL photo
    if canonical_url != url:
        print(f"  ↪️ Navigation vers le permalien : {canonical_url}")
        await page.goto(canonical_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2000)

    # 3. Extraction des métadonnées du post (auteur, date, texte)
    metadata = await extract_post_metadata(page)

    # 4. Création et enregistrement du fichier info_post.json
    info_data = {
        "canonical_url": canonical_url,
        "author": metadata["author"],
        "date": metadata["date"],
        "text": metadata["text"],
        "total_photos": len(photo_files),
        "photo_files": photo_files
    }

    save_post_data(post_folder, info_data)
    return canonical_url


async def enrich_facebook_batch(urls: list[str], state_path: Path = FB_STATE_PATH) -> list[str]:
    """
    Traite un lot d'URLs Facebook en réutilisant la même session Playwright.
    """
    if not Path(state_path).exists():
        raise FileNotFoundError(f"❌ Session introuvable : '{state_path}'.")

    processed_permalinks = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=state_path,
            user_agent=USER_AGENT
        )
        page = await context.new_page()

        # Blocage des polices lourdes pour accélérer les chargements
        await page.route("**/*.{woff,woff2,ttf,otf}", lambda route: route.abort())

        for url in urls:
            try:
                permalink = await process_facebook_photo_url(page, url)
                processed_permalinks.append(permalink)
            except Exception as e:
                print(f"  ⚠️ Erreur lors du traitement de {url} : {e}")

        await browser.close()

    return processed_permalinks


if __name__ == "__main__":
    # Test autonome sur un lot de liens
    async def _test():
        sample_urls = [
            "https://www.facebook.com/photo/?fbid=122175817784924408",
            "https://www.facebook.com/photo/?fbid=954322050789817",
        ]
        print("--- TEST AUTONOME ENRICHER FACEBOOK ---")
        await enrich_facebook_batch(sample_urls)


    asyncio.run(_test())