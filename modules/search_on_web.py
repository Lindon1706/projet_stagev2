from ddgs import DDGS


def find_info(event_name: str,site = "instagram.com"):
    results = []
    query = f'"{event_name}" site:"{site}"'

    print(f"Lancement de la recherche pour le projet : {event_name}")

    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=15):
            results.append({
                'projet': event_name,
                'titre': r.get('title'),
                'extrait': r.get('body'),
                'url': r.get('href')
            })

    return results