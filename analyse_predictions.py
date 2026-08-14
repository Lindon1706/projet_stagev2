import json
import glob
import os
import re
from datetime import datetime

ig_files = glob.glob('data/posts_instagram/*/info_post.json')
fb_files = glob.glob('data/posts_facebook/*/info_post.json')

all_posts = []

for f in ig_files:
    with open(f, encoding='utf-8') as fp:
        try:
            d = json.load(fp)
            d['source'] = 'Instagram'
            all_posts.append(d)
        except Exception:
            pass

for f in fb_files:
    with open(f, encoding='utf-8') as fp:
        try:
            d = json.load(fp)
            d['source'] = 'Facebook'
            all_posts.append(d)
        except Exception:
            pass

print(f"Total des publications analysées : {len(all_posts)}")

# Tri par date
def parse_date(d_str):
    if not d_str:
        return datetime.min
    try:
        return datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.min

all_posts.sort(key=lambda x: parse_date(x.get('date')), reverse=True)

print("\n--- TIMELINE DE EXTRACTION ET PATTERNS DÉTECTÉS ---")
events_found = []

for p in all_posts:
    txt = p.get('text', '')
    dt = p.get('date', '')
    auth = p.get('author', '')
    src = p.get('source')
    url = p.get('canonical_url', '')

    # Détection de dates dans le futur par rapport aux posts
    # Ex: 19 DECEMBRE 2026, 19 septembre, etc.
    dates_matches = re.findall(r'(\d{1,2}\s+(?:JANVIER|FÉVRIER|MARS|AVRIL|MAI|JUIN|JUILLET|AOÛT|SEPTEMBRE|OCTOBRE|NOVEMBRE|DÉCEMBRE|DECEMBRE)\s+\d{4})', txt, re.IGNORECASE)
    
    if dates_matches or any(k in txt.lower() for k in ['tour', 'concert', 'album', 'single', 'salo', 'part 1', 'joÿa', 'cameroun', 'réunion']):
        events_found.append({
            'date_post': dt,
            'author': auth,
            'source': src,
            'text_snippet': txt.strip().replace('\n', ' ')[:150],
            'dates_extracted': dates_matches
        })

print(f"Nombre de publications pertinentes pour la prédiction : {len(events_found)}")
for e in events_found[:15]:
    print(f"[{e['date_post']}] @{e['author']} ({e['source']}): {e['text_snippet']}")
    if e['dates_extracted']:
        print(f"   -> Dates repérées : {e['dates_extracted']}")

