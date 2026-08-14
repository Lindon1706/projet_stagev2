# Documentation du projet

## Objectif
Récolter des données en ligne a propos d'un artiste ou d'un évènement et les insérer dans un système RAG afin d'en dégager de potentiels évènements et calculer la probabilité qu'ils se réalisent
## Étape 1 : Collecte des données
**Principe :** Les données sont extraites depuis des réseaux sociaux via la recherche de Hashtag ou directement depuis les profils des artistes, labels, organisateurs etc via un ensemble de fonctions structurées et rangées dans le dossier modules.  
**Situation :** Pour l'instant on s'est limité à facebook et instagram.  
### **Le dossier modules**: contient toutes les fonctions permettant l'extraction
**il s'agit de**:  
>`harvester.py` 
>>**harvest_instagram(hashtag: str, limit: int = N) -> list[str]:**  
>>récupère les N premiers liens obtenus lors de la recherche de #hashtag sur instagram  
>
>>**harvest_facebook(hashtag: str, limit: int = N) -> list[str]:**  
>>récupère les N premiers liens obtenus lors de la recherche de #hashtag sur facebook
 
>`profile_harvester.py` 
>> **harvest_instagram_profile(
        profile_url_or_username: str,
        limit: int = 10
) -> List[str]:**  
>>renvoie les urls des N derlières publications d'un profil instagram à partir du nom de l'utilisateur ou de l'url de son profil
> 
> >**harvest_facebook_profile(
        profile_url_or_slug: str,
        limit: int = 10
) -> List[str]:**  
>>renvoie les N dernières publications d'un compte facebook à partir de l'url de son profil

>`enricher_fb.py`
>>**extract_post_metadatapage: Page) -> dict:**  
>>récupère les informations d'une publication à partir de son url
> 
>>**process_facebook_photo_url(page: Page, url: str) -> str:**  
>>utilise le lien d'une photo pour récupérer l'url de la publication dont elle est issue
> 
>>**enrich_facebook_batch(urls: list[str], state_path: Path = FB_STATE_PATH) -> list[str]:**  
>>récupère les liens des publications dont sont issus les medias d'une liste

>`enricher_insta.py` 
>>**extract_shortcode(url: str) -> Optional[str]:**  
>>extrait l'identifiant d'une publication à partir de son url
> 
>>**download_image(url: str, target_path: Path) -> bool:**  
>>essaie de télécharger l'image de la publication d'url dans le dossier target path
> 
>>**get_instaloader_instance(
    username: Optional[str] = None,
    session_file: Optional[Path] = None
) -> instaloader.Instaloader:**  
>> Initialise une instance d'Instaloader optimisée pour la vitesse.  
    Tente de charger une session enregistrée si un nom d'utilisateur est fourni.
> 
>>**process_instagram_post_url(
    L: instaloader.Instaloader,
    url: str
) -> Optional[str]:**  
>>permet de récupérer et stocker les informations d'un post
> 
>>**enrich_instagram_batch(
    urls: List[str],
    username: Optional[str] = None,
    session_file: Optional[Path] = None
) -> List[str]:**  
>>permet de récupérer et sauvegarder les informations d'un lot de posts
 
>`storage.py`
>>**BASE_DATA_DIR_FB :**  
>>dossier de stockage des données facebook  
> 
>>**BASE_DATA_DIR_INSTA:**  
>>dosier de stockage des données instagram
> 
>>**sanitize_folder_name(canonical_url: str) -> str:**  
>>Génère un nom de dossier à partir de l'url d'une publication
> 
>>**download_image_from_page(page: Page, target_filepath: Path) -> bool:**  
>>Attend que la page se charge et télécharge l'image
> 
>>**save_post_data(post_folder: Path, info_data: dict):**  
>>permet de sauvegarder les données extraites d'une publication selon l'architecture choisie

>`utils.py`  
>>**clean_facebook_url(url: str) -> str:**  
>>filtre les urls obtenues sur facebook via playwright pour ne garder que celles dont on a besoin 
> 
>>**get_canonical_permalink(page) -> str:**  
>>Cherche le lien 'Afficher la publication' sur la page photo Facebook   et retourne l'URL canonique propre.