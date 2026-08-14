import json
import re
import urllib.request
from pathlib import Path
from typing import List, Optional
import instaloader

from modules.storage import BASE_DATA_DIR_INSTA, save_post_data


def extract_shortcode(url: str) -> Optional[str]:
    """
    Extrait le shortcode Instagram à partir d'une URL de post, reel ou TV.
    """
    match = re.search(r'/(?:p|reel|reels|tv)/([^/?#&]+)', url)
    if match:
        return match.group(1)
    return None


def download_image(url: str, target_path: Path) -> bool:
    """
    Télécharge une image HD depuis une URL directe vers target_path.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response, open(target_path, "wb") as out_file:
            out_file.write(response.read())
        return True
    except Exception as e:
        print(f"  ⚠️ Erreur lors du téléchargement de l'image ({url}) : {e}")
        return False


def get_instaloader_instance(
    username: Optional[str] = None,
    session_file: Optional[Path] = None
) -> instaloader.Instaloader:
    """
    Initialise une instance d'Instaloader optimisée pour la vitesse.
    Tente de charger une session enregistrée si un nom d'utilisateur est fourni.
    """
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True
    )

    if username:
        try:
            if session_file and Path(session_file).exists():
                L.load_session_from_file(username, filename=str(session_file))
            else:
                L.load_session_from_file(username)
            print(f"  🔓 Session Instaloader chargée pour l'utilisateur : {username}")
        except Exception as e:
            print(f"  ⚠️ Impossible de charger la session ({e}). Continuation en mode public...")

    return L


def process_instagram_post_url(
    L: instaloader.Instaloader,
    url: str
) -> Optional[str]:
    """
    Traite une URL Instagram :
    1. Extrait le shortcode unique.
    2. Récupère la publication via Instaloader.
    3. Crée le dossier local sous BASE_DATA_DIR_INSTA / post_<shortcode>.
    4. Télécharge les images HD (image unique ou carrousel).
    5. Sauvegarde info_post.json avec l'auteur, la date, le texte et la liste des images.
    """
    shortcode = extract_shortcode(url)
    if not shortcode:
        print(f"  ⚠️ URL Instagram invalide ou shortcode introuvable : {url}")
        return None

    canonical_url = f"https://www.instagram.com/p/{shortcode}/"
    folder_name = f"post_{shortcode}"
    post_folder = BASE_DATA_DIR_INSTA / folder_name
    json_path = post_folder / "info_post.json"

    print(f"\n🔍 [Enricher IG] Traitement de : {canonical_url}")

    # Vérification si la publication a déjà été traitée
    if json_path.exists():
        print(f"  📂 Dossier existant trouvé : {folder_name}")
        return canonical_url

    try:
        # Récupération de l'objet Post depuis l'API d'Instaloader
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        author = post.owner_username or ""
        date_str = post.date_utc.strftime("%Y-%m-%d %H:%M:%S") if post.date_utc else ""
        text = post.caption or ""

        # Récupération des URLs d'images (Gestion des Carrousels vs Images uniques)
        image_urls = []
        if post.typename == "GraphSidecar":
            for node in post.get_sidecar_nodes():
                if not node.is_video and node.display_url:
                    image_urls.append(node.display_url)
        else:
            if not post.is_video and post.url:
                image_urls.append(post.url)

        # Création du dossier et téléchargement des images
        post_folder.mkdir(parents=True, exist_ok=True)
        photo_files = []

        for idx, img_url in enumerate(image_urls, start=1):
            photo_filename = f"photo_{idx}.jpg"
            target_path = post_folder / photo_filename
            if download_image(img_url, target_path):
                photo_files.append(photo_filename)
                print(f"  📸 Image enregistrée : {photo_filename}")

        # Enregistrement des données de la publication
        info_data = {
            "canonical_url": canonical_url,
            "shortcode": shortcode,
            "author": author,
            "date": date_str,
            "text": text,
            "total_photos": len(photo_files),
            "photo_files": photo_files
        }

        save_post_data(post_folder, info_data)
        return canonical_url

    except Exception as e:
        print(f"  ⚠️ Erreur lors de l'extraction de {url} : {e}")
        return None


def enrich_instagram_batch(
    urls: List[str],
    username: Optional[str] = None,
    session_file: Optional[Path] = None
) -> List[str]:
    """
    Traite un lot d'URLs Instagram en réutilisant l'instance Instaloader.
    """
    L = get_instaloader_instance(username=username, session_file=session_file)
    processed_permalinks = []

    for url in urls:
        permalink = process_instagram_post_url(L, url)
        if permalink:
            processed_permalinks.append(permalink)

    return processed_permalinks


if __name__ == "__main__":
    # Test autonome rapide
    sample_urls = [
        "https://www.instagram.com/p/C_abc123/",
    ]
    print("--- TEST AUTONOME ENRICHER INSTAGRAM ---")
    enrich_instagram_batch(sample_urls)