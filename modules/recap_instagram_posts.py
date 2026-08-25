import os
import json
import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def extract_post_data(json_path: Path, folder_name: str) -> Optional[Dict[str, Any]]:

    try:
        with open(json_path, mode="r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[AVERTISSEMENT] Erreur lors de la lecture de {json_path} : {e}")
        return None

    # Extraction et découpage de la date / heure si disponible
    raw_date = data.get("date", "")
    date_str = ""
    heure_str = ""
    if raw_date:
        parts = raw_date.strip().split()
        if len(parts) >= 1:
            date_str = parts[0]
        if len(parts) >= 2:
            heure_str = parts[1]

    # Formatage des fichiers photos
    photo_files = data.get("photo_files", [])
    if isinstance(photo_files, list):
        photo_files_str = "; ".join(photo_files)
    else:
        photo_files_str = str(photo_files)

    return {
        "folder": folder_name,
        "post_folder": json_path.parent.name,
        "shortcode": data.get("shortcode", ""),
        "canonical_url": data.get("canonical_url", ""),
        "author": data.get("author", ""),
        "date": date_str,
        "heure": heure_str,
        "datetime": raw_date,
        "text": data.get("text", ""),
        "total_photos": data.get("total_photos", len(photo_files) if isinstance(photo_files, list) else 0),
        "photo_files": photo_files_str,
        "type": "posts_instagram"
    }


def compile_instagram_posts_to_csv(
    folders: Optional[List[str]] = None,
    data_dir: str = "data",
    output_csv: str = "data/Save_csv/recap_instagram.csv",
    sort_by_date: bool = True
) -> List[Dict[str, Any]]:

    base_path = Path(data_dir)
    if not base_path.exists() or not base_path.is_dir():
        raise FileNotFoundError(f"Le dossier de données '{data_dir}' n'existe pas.")

    # Si aucun dossier n'est fourni, on détecte automatiquement les sous-dossiers
    if not folders:
        folders = [
            d.name for d in base_path.iterdir()
            if d.is_dir() and (d / "posts_instagram").is_dir()
        ]
        folders.sort()

    print(f"[*] Dossiers ciblés ({len(folders)}) : {', '.join(folders)}")

    records: List[Dict[str, Any]] = []

    for folder_name in folders:
        folder_path = base_path / folder_name
        ig_path = folder_path / "posts_instagram"

        if not ig_path.exists() or not ig_path.is_dir():
            print(f"[-] Sous-dossier non trouvé ou ignoré : {ig_path}")
            continue

        json_files = list(ig_path.glob("*/info_post.json"))
        print(f"[+] '{folder_name}' : {len(json_files)} publications Instagram trouvées.")

        for json_file in json_files:
            post_data = extract_post_data(json_file, folder_name)
            if post_data:
                records.append(post_data)

    print(f"[*] Total des publications extraites : {len(records)}")

    # Tri par date décroissante
    if sort_by_date:
        def get_sort_key(item: Dict[str, Any]):
            dt_str = item.get("datetime", "")
            try:
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return datetime.min

        records.sort(key=get_sort_key, reverse=True)

    # Écriture du fichier CSV
    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "folder",
        "post_folder",
        "shortcode",
        "canonical_url",
        "author",
        "date",
        "heure",
        "total_photos",
        "photo_files",
        "type",
        "text"
    ]

    with open(out_path, mode="w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    print(f"[✓] Fichier CSV récapitulatif généré avec succès : {out_path.resolve()}")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Contracte les JSON info_post.json Instagram d'une liste de dossiers en un seul CSV récapitulatif."
    )
    parser.add_argument(
        "-f", "--folders",
        nargs="+",
        help="Noms des dossiers situés dans 'data/' à traiter (ex: --folders Canal2Or musicinafrica FallyIpupa)."
    )
    parser.add_argument(
        "-d", "--data-dir",
        default="data",
        help="Chemin du dossier racine des données (défaut: 'data')."
    )
    parser.add_argument(
        "-o", "--output",
        default="data/Save_csv/recap_instagram.csv",
        help="Chemin du fichier CSV de sortie (défaut: 'data/Save_csv/recap_instagram.csv')."
    )

    args = parser.parse_args()

    compile_instagram_posts_to_csv(
        folders=args.folders,
        data_dir=args.data_dir,
        output_csv=args.output
    )
