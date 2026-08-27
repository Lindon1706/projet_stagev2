from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import re
import pandas as pd

mois_fr = {
    "janvier" : "01",
    "février" : "02",
    "mars" : "03",
    "avril" : "04",
    "mai" : "05",
    "juin" : "06",
    "juillet" : "07",
    "août" : "08",
    "septembre" : "09",
    "octobre" : "10",
    "novembre" : "11",
    "décembre" : "12",
}

def format_date_fr(date_string : str):
    if date_string:
        if "à" in date_string:
            date_part, hour = date_string.split("à",1)
        else:
            date_part, hour = date_string.split()
            return {"date": date_part, "heure": hour}
        match = re.search(r"(\d{1,2})\s+([a-zA-Zà-ÿ]+)\s+(\d{4})", date_part)
        if match:
            day, month, year = match.groups()
            num_month = mois_fr.get(month.lower(),"01")
            date_iso = f"{year}-{int(num_month):02d}-{int(day):02d}"
        else:
            date_iso = date_part.strip()
        return {"date" : date_iso, "heure" : hour}
    return { "date" : "" , "heure" : "" }


def clean_facebook_url(url: str) -> str:
    blacklist = ["/search/", "/watch/hashtag/", "/explore/","/reels","/reel"]
    if any(bad in url for bad in blacklist):
        return ""

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    query_params = parse_qs(parsed.query)

    if path in ["/photo", "/photos", "/photo.php"]:
        if "fbid" in query_params:
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?fbid={query_params['fbid'][0]}"
        return ""

    if path in ["", "/reel", "/reels", "/watch", "/hashtag"]:
        return ""

    if any(
        k in path for k in ["/posts/", "pfbid", "/videos/", "/reel/", "/groups/"]
    ):
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    essential_params = {}
    for key in ["story_fbid", "fbid", "id", "v"]:
        if key in query_params:
            essential_params[key] = query_params[key][0]

    if "story_fbid" in essential_params or "fbid" in essential_params:
        new_query = urlencode(essential_params)
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", new_query, "")
        )

    return ""


def clean_permalink_url(href: str) -> str:
    """
    Nettoie l'URL du permalien :
    - Pour 'permalink.php' : conserve 'story_fbid' ET 'id' (obligatoires).
    - Pour les URLs /posts/ ou /groups/ : conserve le chemin d'accès propre sans tracking.
    """
    parsed = urlparse(href)

    # 1. Cas des permaliens sous forme permalink.php?story_fbid=...&id=...
    if "permalink.php" in parsed.path:
        query_params = parse_qs(parsed.query)
        clean_params = {}

        if "story_fbid" in query_params:
            clean_params["story_fbid"] = query_params["story_fbid"][0]
        if "id" in query_params:
            clean_params["id"] = query_params["id"][0]

        new_query = urlencode(clean_params)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ''))

    # 2. Cas des permaliens sous forme /groups/xxx/permalink/yyy/ ou /username/posts/yyy/
    else:
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))


async def get_canonical_permalink(page) -> str:
    """
    Cherche le lien 'Afficher la publication' sur la page photo Facebook
    et retourne l'URL canonique propre.
    """
    selectors = [
        'a:has-text("Afficher la publication")',
        'a:has-text("View post")',
        'a[href*="permalink.php"]',
        'a[href*="/posts/"]',
        'a[href*="/groups/"]'
    ]

    for selector in selectors:
        element = await page.query_selector(selector)
        if element:
            href = await element.get_attribute("href")
            if href:
                # Reconstitution de l'URL absolue si lien relatif
                if href.startswith("/"):
                    href = f"https://www.facebook.com{href}"

                return clean_permalink_url(href)

    return page.url

def parse_stat_to_num(val):
    if pd.isna(val) or not val:
        return 0.0
    val_str = str(val).lower().replace(',', '.').replace(' ', '').strip()
    multiplier = 1.0

    if 'k' in val_str:
        multiplier = 1_000.0
        val_str = val_str.replace('k', '')
    elif 'm' in val_str:
        multiplier = 1_000_000.0
        val_str = val_str.replace('m', '')
    elif 'b' in val_str:
        multiplier = 1_000_000_000.0
        val_str = val_str.replace('b', '')

    try:
        clean_num = re.sub(r'[^0-9.]', '', val_str)
        return float(clean_num) * multiplier
    except ValueError:
        return 0.0

