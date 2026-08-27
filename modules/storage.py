import pandas as pd
import json
import re
from pathlib import Path
from playwright.async_api import Page
from modules.utils import format_date_fr


BASE_DATA_DIR_FB = Path(__file__).resolve().parent.parent / "data" / "posts_facebook"
BASE_DATA_DIR_INSTA = Path(__file__).resolve().parent.parent / "data" / "posts_instagram"


def sanitize_folder_name(canonical_url: str) -> str:
    numbers = re.findall(r'\d+', canonical_url)
    if numbers:
        folder_id = "_".join(numbers[-2:])
        return f"post_{folder_id}"

    clean = re.sub(r'[^\w\-_]', '_', canonical_url)
    return f"post_{clean[:50]}"


async def download_image_from_page(page: Page, target_filepath: Path) -> bool:
    """
    Télécharge l'image HD avec attente explicite du chargement + fallback.
    """
    try:
        # Sélecteurs d'images HD Facebook par ordre de priorité
        selectors = [
            'img[data-visualcompletion="media-vc-image"]',
            'div[role="dialog"] img[src*="scontent"]',
            'div[role="main"] img[src*="scontent"]',
            'img[src*="scontent"]'
        ]

        src = None

        # 1. Attente active de l'image dans le DOM (jusqu'à 5 secondes)
        for sel in selectors:
            try:
                img_element = await page.wait_for_selector(sel, timeout=5000)
                if img_element:
                    src = await img_element.get_attribute("src")
                    if src:
                        break
            except Exception:
                continue

        # 2. Sécurité / Fallback : Méta-balise OpenGraph de la page
        if not src:
            meta_element = await page.query_selector('meta[property="og:image"]')
            if meta_element:
                src = await meta_element.get_attribute("content")

        if not src:
            print("  ⚠️ Aucune URL d'image détectée.")
            return False

        # Téléchargement de l'image
        response = await page.request.get(src)
        if response.status == 200:
            target_filepath.write_bytes(await response.body())
            return True

    except Exception as e:
        print(f"  ⚠️ Erreur lors du téléchargement de l'image : {e}")

    return False


def save_post_data(post_folder: Path, info_data: dict):
    post_folder.mkdir(parents=True, exist_ok=True)
    json_path = post_folder / "info_post.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(info_data, f, ensure_ascii=False, indent=2)

    print(f"  💾 Données enregistrées : {json_path}")



def concat_account_info(file_path : str) -> pd.DataFrame:
    df = pd.read_json(file_path, lines=True)
    df['posts'] = df['stats'].apply(lambda x: x.get('posts') if isinstance(x, dict) else None)
    df["followers"] = df["stats"].apply(lambda x: x.get("followers") if isinstance(x, dict) else None)
    df["following"] = df["stats"].apply(lambda x: x.get("following") if isinstance(x, dict) else None)
    df["num_link"] = df["externalLinks"].apply(lambda x: len(x) if isinstance(x, list) else None)
    return df