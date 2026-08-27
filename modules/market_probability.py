import sys
import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

from modules.storage import concat_account_info
from modules.utils import parse_stat_to_num

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
DELAY_SECONDS = 3

class OutcomeProbability(BaseModel):
    outcome: str = Field(
        description="Nom exact de l'issue du marché (ex: 'Oui', 'Non', 'Moins de 30 pays')"
    )
    probability: float = Field(
        description="Probabilité estimée de l'issue entre 0.0 et 1.0 (la somme de toutes les issues doit être égale à 1.0)"
    )

class FullMarket(BaseModel):
    mkt_name: str = Field(
        description="Nom ou intitulé du marché"
    )
    mkt_question: str = Field(
        description="Question formulée pour le marché"
    )
    mkt_solvability: str = Field(
        description="Critère permettant de résoudre l'issue du marché"
    )
    mkt_type: str = Field(
        description="'binary' (Oui/Non) ou 'categorical' (plusieurs options)"
    )
    mkt_outcomes: Dict[str, float] = Field(
        default_factory=dict,
        description="Dictionnaire associant chaque issue à sa probabilité normalisée (somme = 1.0). Ex: {'Oui': 0.85, 'Non': 0.15}"
    )
    mkt_closing_date: Optional[str] = Field(
        default=None,
        description="Date et heure ISO estimées de clôture du marché"
    )
    mkt_rating: int = Field(
        default=5,
        description="Note de viabilité du marché (entre 0 et 10)"
    )

class LLMMarketProbabilityResponse(BaseModel):
    mkt_name: str = Field(description="Nom du marché")
    outcomes_probabilities: List[OutcomeProbability] = Field(
        description="Liste des issues, de leurs probabilités estimées et de leurs justifications spécifiques"
    )

class Event(BaseModel):
    evt_name: str
    evt_status: str
    evt_description: str
    evt_date: str
    evt_category: str
    source_posts_id: List[int] = Field(default_factory=list)

class EventWithFullMarket(BaseModel):
    event: Event
    markets: List[FullMarket] = Field(default_factory=list)

SYSTEM_INSTRUCTION_PROBABILITY_ESTIMATION = """Tu es une IA experte en analyse prédictive et modélisation probabiliste pour des marchés de prédiction culturels (style Polymarket).

Ton objectif est d'estimer avec précision la probabilité de chaque issue possible d'un marché donné, en te fondant rigoureusement sur les faits rapportés dans les publications sources et sur l'autorité/indice d'influence de leurs auteurs.

**Directives méthodologiques :**
1. **Analyse de position & factualité :** Identifie si la publication confirme formellement l'événement, annonce une date officielle, rapporte une rumeur, ou exprime une incertitude.
2. **Pondération par l'indice d'influence :** 
   - Un compte officiel ou un média certifié avec un fort indice d'influence (ex: indice > 100, compte vérifié) a un poids probant très élevé (certitude de l'annonce officielle).
   - Les comptes de fans ou non certifiés avec faible indice ont un poids plus indicatif.
3. **Distribution des probabilités :**
   - La somme des probabilités de toutes les issues doit égaler 1.0 (ou 100%).
   - Pour un marché binaire ['Oui', 'Non'] où une annonce officielle est déjà faite par l'organisateur ou l'artiste, l'issue 'Oui' est hautement probable (ex: 0.80 à 0.95), tout en conservant une marge pour les aléas (report, annulation, imprévu).
   - Sois réaliste et nuancé pour les marchés d'audience ou de performance (ex: 1 million de vues en 24h, victoire à une cérémonie).
"""


def compute_full_data(
        authors_file: Union[str, Path] = "data/info_save/all_profiles.jsonl",
        posts_file: Union[str, Path] = "data/Save_csv/recap_instagram.csv",
        gamma: float = 0.40
) -> pd.DataFrame:
    """
    Calcule l'indice d'influence pour chaque profil et l'associe aux publications.

    Formule :
    - base_reach = followers ** gamma (gamma = 0.40)
    - ratio = followers / (1 + following)
    - m_ratio = 1 + tanh(ln(1 + ratio))
    - m_auth = 1.0 + (0.50 * isVerified) + (0.15 * has_bio) + (0.15 * has_links)
    - influence_index = base_reach * m_ratio * m_auth
    """
    authors_path = Path(authors_file)
    if not authors_path.is_absolute():
        authors_path = PROJECT_ROOT / authors_path

    posts_path = Path(posts_file)
    if not posts_path.is_absolute():
        posts_path = PROJECT_ROOT / posts_path

    if not authors_path.exists():
        raise FileNotFoundError(f"Fichier profils introuvable : {authors_path}")
    if not posts_path.exists():
        raise FileNotFoundError(f"Fichier publications introuvable : {posts_path}")

    # 1. Chargement des profils et extraction numérique des statistiques
    infos = concat_account_info(str(authors_path))
    infos['followers_num'] = infos['followers'].apply(parse_stat_to_num)
    infos['following_num'] = infos['following'].apply(parse_stat_to_num)

    followers = infos['followers_num']
    following = infos['following_num']

    # 2. Calcul de la portée de base
    base_reach = np.power(followers, gamma)

    # 3. Multiplicateur de sélectivité (Ratio followers / following)
    ratio = followers / (1.0 + following)
    m_ratio = 1.0 + np.tanh(np.log(1.0 + np.maximum(ratio, 0.0)))

    # 4. Multiplicateur d'autorité
    has_verified = infos['isVerified'].fillna(False).astype(int) if 'isVerified' in infos else 0
    has_bio = (infos['bio'].fillna('').str.strip().str.len() >= 10).astype(int) if 'bio' in infos else 0
    has_links = infos['externalLinks'].apply(
        lambda x: len(x) > 0 if isinstance(x, list) else False
    ).astype(int) if 'externalLinks' in infos else 0

    m_auth = 1.0 + (0.50 * has_verified) + (0.15 * has_bio) + (0.15 * has_links)

    # 5. Indice d'influence final
    infos['influence_index'] = base_reach * m_ratio * m_auth

    # Dédoublonnage par nom d'utilisateur
    infos_unique = infos.drop_duplicates(subset=['username']).copy()

    # 6. Fusion avec les publications
    posts = pd.read_csv(posts_path)
    all_data = posts.merge(
        infos_unique,
        left_on='author',
        right_on='username',
        how='left'
    )

    # Valeurs par défaut pour les auteurs sans métadonnées
    all_data['influence_index'] = all_data['influence_index'].fillna(1.0)
    all_data['followers_num'] = all_data['followers_num'].fillna(0.0)
    all_data['following_num'] = all_data['following_num'].fillna(0.0)
    all_data['isVerified'] = all_data['isVerified'].fillna(False)
    all_data['bio'] = all_data['bio'].fillna('')

    print(f"✅ Données consolidées : {len(all_data)} publications avec indices d'influence calculés.")
    return all_data

def normalize_outcomes_probabilities(
    raw_probs: List[OutcomeProbability],
    expected_outcomes: List[str]
) -> Dict[str, float]:

    prob_dict = {}
    for item in raw_probs:
        p = float(item.probability)
        if p > 1.0:
            p = p / 100.0  # Conversion pourcentage vers probabilité
        p = max(0.001, min(0.999, p))
        prob_dict[item.outcome.strip()] = p

    # Vérification des issues manquantes
    for exp in expected_outcomes:
        exp_clean = exp.strip()
        if exp_clean not in prob_dict:
            matched = False
            for k in list(prob_dict.keys()):
                if k.lower() == exp_clean.lower():
                    prob_dict[exp_clean] = prob_dict.pop(k)
                    matched = True
                    break
            if not matched:
                prob_dict[exp_clean] = 0.05

    # Filtrer uniquement les issues attendues
    final_dict = {}
    for exp in expected_outcomes:
        exp_clean = exp.strip()
        final_dict[exp_clean] = prob_dict.get(exp_clean, 1.0 / len(expected_outcomes))

    # Normalisation somme = 1.0
    total = sum(final_dict.values())
    if total > 0:
        normalized = {k: round(v / total, 3) for k, v in final_dict.items()}
    else:
        normalized = {k: round(1.0 / len(expected_outcomes), 3) for k in expected_outcomes}

    # Ajustement d'arrondi sur la dernière issue pour garantir somme exacte = 1.0
    diff = round(1.0 - sum(normalized.values()), 3)
    if diff != 0 and normalized:
        first_key = next(iter(normalized))
        normalized[first_key] = round(normalized[first_key] + diff, 3)

    return normalized

def generate_market_probabilities(
    event_data: Dict[str, Any],
    market_data: Dict[str, Any],
    df_info: pd.DataFrame,
    client: genai.Client,
    model_name: str = DEFAULT_MODEL,
    max_attempts: int = 4
) -> FullMarket:

    mkt_name = market_data.get("mkt_name", "")
    mkt_question = market_data.get("mkt_question", "")
    mkt_solvability = market_data.get("mkt_solvability", "")
    mkt_type = market_data.get("mkt_type", "binary")
    expected_outcomes = market_data.get("mkt_outcomes", ["Oui", "Non"])
    mkt_closing_date = market_data.get("mkt_closing_date")
    mkt_rating = market_data.get("mkt_rating", 5)

    source_post_ids = event_data.get("source_posts_id", [])

    # Extraction des détails des publications sources
    source_posts_context = []
    for pid in source_post_ids:
        if 0 <= pid < len(df_info):
            row = df_info.iloc[pid]
            source_posts_context.append({
                "id_publication": int(pid),
                "auteur": str(row.get("author", "inconnu")),
                "compte_verifie": bool(row.get("isVerified", False)),
                "followers": int(row.get("followers_num", 0)),
                "following": int(row.get("following_num", 0)),
                "indice_influence": round(float(row.get("influence_index", 1.0)), 2),
                "bio": str(row.get("bio", "")),
                "date": str(row.get("date", "")),
                "heure": str(row.get("heure", "")),
                "texte_publication": str(row.get("text", ""))
            })

    # Construction du prompt d'analyse
    prompt = f"""
Voici les informations de l'événement et du marché à évaluer :

ÉVÉNEMENT :
- Nom : {event_data.get('evt_name', '')}
- Catégorie : {event_data.get('evt_category', '')}
- Date prévue : {event_data.get('evt_date', '')}
- Description : {event_data.get('evt_description', '')}

MARCHÉ DE PRÉDICTION :
- Nom du marché : {mkt_name}
- Question posée : {mkt_question}
- Critère de solvabilité : {mkt_solvability}
- Type de marché : {mkt_type}
- Issues possibles à évaluer : {expected_outcomes}
- Date estimée de clôture : {mkt_closing_date}
- Note du marché : {mkt_rating}/10

PUBLICATIONS SOURCES ET INDICES D'INFLUENCE DES AUTEURS :
{json.dumps(source_posts_context, ensure_ascii=False, indent=2)}

Estime la probabilité de chaque issue possible parmi {expected_outcomes} en prenant en compte l'indice d'influence de chaque auteur.
Donne pour chaque issue une justification concise (reasoning), ainsi qu'une synthèse explicative globale (rationale).
"""

    llm_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION_PROBABILITY_ESTIMATION,
        response_mime_type="application/json",
        response_schema=LLMMarketProbabilityResponse,
        temperature=0.2
    )

    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=llm_config
            )
            parsed: Optional[LLMMarketProbabilityResponse] = response.parsed
            if parsed and parsed.outcomes_probabilities:
                normalized_probs = normalize_outcomes_probabilities(
                    parsed.outcomes_probabilities,
                    expected_outcomes
                )

                """# Récupération des explications par issue
                outcome_explanations = {
                    item.outcome.strip(): item.reasoning
                    for item in parsed.outcomes_probabilities
                    if item.reasoning
                }"""

                return FullMarket(
                    mkt_name=mkt_name,
                    mkt_question=mkt_question,
                    mkt_solvability=mkt_solvability,
                    mkt_type=mkt_type,
                    mkt_outcomes=normalized_probs,
                    mkt_closing_date=mkt_closing_date,
                    mkt_rating=mkt_rating,
                )
        except Exception as e:
            print(f"  ⚠️ Tentative {attempt}/{max_attempts} échouée pour '{mkt_name}' : {e}")
            time.sleep(DELAY_SECONDS)

    # Fallback si échec après toutes les tentatives
    print(f"  ❌ Échec d'estimation LLM pour '{mkt_name}', application d'une distribution équiprobable.")
    fallback_probs = {k: round(1.0 / len(expected_outcomes), 3) for k in expected_outcomes}
    return FullMarket(
        mkt_name=mkt_name,
        mkt_question=mkt_question,
        mkt_solvability=mkt_solvability,
        mkt_type=mkt_type,
        mkt_outcomes=fallback_probs,
        mkt_closing_date=mkt_closing_date,
        mkt_rating=mkt_rating,
    )


def process_events_and_add_probabilities(
    input_json: Union[str, Path] = "data/Save_csv/test_dir/test_ouput.json",
    output_json: Optional[Union[str, Path]] = None,
    authors_file: Union[str, Path] = "data/info_save/all_profiles.jsonl",
    posts_file: Optional[Union[str, Path]] = None,
    model_name: str = DEFAULT_MODEL,
) -> Dict[str, Any]:

    input_path = Path(input_json)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    if not input_path.exists():
        raise FileNotFoundError(f"Fichier d'entrée introuvable : {input_path}")

    # Clé API récupérée via os.environ.get
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Clé API Gemini non fournie. Veuillez définir la variable GEMINI_API_KEY dans os.environ.")

    client = genai.Client(api_key=api_key)

    # Lecture du fichier d'entrée
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Détermination automatique du fichier source des publications si non spécifié
    if posts_file is None:
        source_from_json = data.get("generation data", {}).get("source_file")
        if source_from_json and Path(source_from_json).exists():
            posts_file = source_from_json
        else:
            posts_file = PROJECT_ROOT / "data/Save_csv/recap_instagram.csv"

    print(" DÉMARRAGE DU CALCUL ET DE L'ANALYSE DES PROBABILITÉS DES MARCHÉS")
    print("\n")
    print(f"📁️ Fichier d'entrée     : {input_path}")
    print(f"📁️ Fichier publications : {posts_file}")
    print(f"📁️ Fichier profils      : {authors_file}")

    # Calcul de l'influence
    df_info = compute_full_data(authors_file=authors_file, posts_file=posts_file)

    events_and_markets_raw = data.get("events and markets", [])
    total_events = len(events_and_markets_raw)
    total_markets = sum(len(e.get("markets", [])) for e in events_and_markets_raw)

    print(f"\n {total_events} événements et {total_markets} marchés à traiter...")

    enriched_events = []
    market_counter = 0

    for ev_idx, item in enumerate(events_and_markets_raw, start=1):
        event_dict = item.get("event", {})
        markets_list = item.get("markets", [])
        evt_name = event_dict.get("evt_name", "Inconnu")

        print(f"\n \n" )
        print(f" ÉVÉNEMENT [{ev_idx}/{total_events}] : {evt_name} ({len(markets_list)} marchés)")
        print("\n")

        full_markets = []
        for mkt_idx, mkt in enumerate(markets_list, start=1):
            market_counter += 1
            mkt_name = mkt.get("mkt_name", "")
            print(f"\n⚡ Calcul des probabilités [{market_counter}/{total_markets}] : '{mkt_name}'...")

            full_mkt = generate_market_probabilities(
                event_data=event_dict,
                market_data=mkt,
                df_info=df_info,
                client=client,
                model_name=model_name
            )


            full_markets.append(full_mkt)
            time.sleep(DELAY_SECONDS)

        # Reconstitution de l'événement complet
        event_obj = Event(
            evt_name=event_dict.get("evt_name", ""),
            evt_status=event_dict.get("evt_status", "open"),
            evt_description=event_dict.get("evt_description", ""),
            evt_date=event_dict.get("evt_date", ""),
            evt_category=event_dict.get("evt_category", "musique"),
            source_posts_id=event_dict.get("source_posts_id", [])
        )

        enriched_events.append(
            EventWithFullMarket(
                event=event_obj,
                markets=full_markets
            )
        )

    # Préparation du résultat final
    if output_json is None:
        output_path = input_path.parent / f"{input_path.stem}_with_probabilities.json"
    else:
        output_path = Path(output_json)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    result_payload = {
        "generation data": {
            "source_events_file": str(input_path),
            "source_posts_file": str(posts_file),
            "authors_profiles_file": str(authors_file),
            "model_used": model_name,
            "total_events": len(enriched_events),
            "total_markets": market_counter
        },
        "events and markets": [
            {
                "event": item.event.model_dump(),
                "markets": [m.model_dump() for m in item.markets]
            }
            for item in enriched_events
        ]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    print("\n \n")
    print(f"✅ TRAITEMENT TERMINÉ AVEC SUCCÈS !")
    print(f"💾 Fichier complet sauvegardé dans : {output_path.resolve()}")
    print("\n")


    return result_payload

if __name__ == "__main__":
    process_events_and_add_probabilities()
