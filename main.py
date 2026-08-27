import json
from pathlib import Path

import pandas as pd

from modules.AI_treatment import evaluate_post, extract_events, generate_markets
from modules.market_probability import process_events_and_add_probabilities


def test():
    dossier_posts = Path("data/extracted_posts")
    fichier_csv = Path("data/Save_csv/all_extracted_posts_ai.csv")
    fichier_marches = Path("data/Save_csv/all_extracted_posts_markets.json")
    fichier_profils = Path("data/info_save/all_profiles.jsonl")
    fichier_probabilites = Path(
        "data/Save_csv/all_extracted_posts_markets_with_probabilities.json"
    )

    publications = []
    for fichier in dossier_posts.rglob("info_post.json"):
        with open(fichier, encoding="utf-8") as f:
            publication = json.load(f)
        publication["id"] = len(publications)
        publications.append(publication)

    publications_df = pd.DataFrame(publications)
    fichier_csv.parent.mkdir(parents=True, exist_ok=True)
    publications_df.to_csv(fichier_csv, index=False)

    publications_evaluees = evaluate_post(
        publications_df,
        text_column="text",
        batch_size=20,
    )
    publications_evaluees.to_csv(fichier_csv, index=False)

    publications_pertinentes = publications_evaluees[
        publications_evaluees["pertinence"] == True
    ]
    evenements = extract_events(
        publications_pertinentes,
        text_column="text",
        batch_size=15,
    )
    evenements_et_marches = generate_markets(
        evenements,
        df_pertinent=publications_pertinentes,
        text_column="text",
    )

    resultat = {
        "events and markets": [
            {
                "event": element.event.model_dump(),
                "markets": [marche.model_dump() for marche in element.markets],
            }
            for element in evenements_et_marches
        ]
    }

    with open(fichier_marches, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    process_events_and_add_probabilities(
        input_json=fichier_marches,
        output_json=fichier_probabilites,
        authors_file=fichier_profils,
        posts_file=fichier_csv,
    )


if __name__ == "__main__":
    test()
