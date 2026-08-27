import os
from google import genai
from google.genai import types
from  pydantic import BaseModel,Field
import pandas as pd
from typing import List, Dict, Any, Optional, Literal, Union
import time
import json
from pathlib import Path
from datetime import datetime
import locale
import zoneinfo
from dotenv import load_dotenv

load_dotenv()


DEFAULT_MODEL = "gemini-3.6-flash"

DELAY_SECONDS = 5

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class SinglePostEvaluation(BaseModel):
    id: int = Field(description="L'identifiant/index d'origine de la publication")
    pertinent: bool = Field(description="True si la publication est pertinente, False sinon")
    raison: str = Field(description="Justification de la décision")

class BatchPostEvaluation(BaseModel):
    evaluations: list[SinglePostEvaluation]

class Event(BaseModel):
    evt_name: str = Field(
        description="nom de l'évènement à venir. Exemple: 'concert de tayc au cameroun' , 'gramy awards 2027','festival des écrans noirs 2026'"
    )
    evt_status:str = Field(
        description=" 'open' si l'évènement a n'a pas encore eu lieu 'close' si l'évènement a déja eu lieu ou est incertain"
    )
    evt_description : str = Field(
        description="donne une description de l'évènement"
    )
    evt_date : str = Field(
        description="donne la date à laquelle l'évènement va se dérouler au format année-mois-jour. Exemple: 2026-08-16"
    )
    evt_category : str = Field(
        description="classe l'évènement dans une catégorie parmi les suivantes [musique,cinéma,artiste,récompense,concert]"
    )
    source_posts_id : List[int] = Field(
        description="liste des identifiants des publications permettant d'identifier l'évènement"
    )

class BatchEvents(BaseModel):
    events : List[Event] = Field(
        description="liste des évènements pertinents identifiés"
    )


class Market(BaseModel):
    mkt_name: str = Field(
        description="nom du marché"
    )
    mkt_question: str = Field(
        description="donne une question claire au marché"
    )
    mkt_solvability: str = Field(
        description="donne un critère pemettant de connaître l'issu du marché"
    )
    mkt_type : str = Field(
        description="'binary' si la réponse à la question est oui ou non,'catégorical' si il y a plusieurs propositions pour la réponse"
    )
    mkt_outcomes : list = Field(
        description="donne la liste des résultats possibles. Exemple: ['Oui','Non']"
    )
    mkt_closing_date: Optional[str] = Field(
        default=None,
        description="Date et heure ISO estimées de clôture du marché"
    )
    mkt_rating : int = Field(
        description="note entre 0 et 10 attribuée à chaque marché mesurant la viabilité de celui-ci"
    )

class BatchMarket(BaseModel):
    markets : List[Market] = Field(
        description="Marchés de prediction formulés"
    )

class EventWithMarket(BaseModel):
    event: Event
    markets : List[Market] = Field(
        default_factory=list
    )

DEFAULT_API_KEY = os.environ.get("GEMINI_API_KEY", "")

#instructions IA
SYSTEM_INSTRUCTION_POST_EVALUATION = """Tu es une IA spécialisée dans l'analyse de publications pour un site de paris sur événements culturels. Ta mission : évaluer si chaque publication est pertinente pour générer un marché de paris.

**Critères de viabilité — une publication est pertinente si elle contient :**

- **Annonce officielle d'un événement futur clairement identifiabler par son nom** : confirmation formelle d'une date, d'une heure et d'un lieu pour un concert, spectacle, performance ou événement culturel à venir.
- **Information d'impact direct sur les participants** : éléments mesurables affectant la participation ou le résultat (blessure confirmée, forfait d'artiste, transfert, suspension, changement de composition, remplacement d'entraîneur ou d'artiste principal)
- **Modifications organisationnelles** : report d'événement, annulation, changement de lieu, changement d'horaire, restriction d'accès ou modification des conditions
- **Déclarations ou événements hors-terrain mesurables** : annonces d'albums, confirmations d'invités surprise, résultats d'élections, remises de prix, collaborations annoncées, ou tout événement concurrent ou complémentaire ouvrant un marché de paris spécifique

**Critères de non-viabilité — rejette les publications contenant :**
- Mèmes, réactions de fans, ou opinions subjectives sans fondement factuel vérifiable
- Rumeurs, spéculations ou affirmations non confirmées par une source officielle
- Contenu promotionnel générique sans information nouvelle ou mesurable
- Commentaires sur des événements passés sans implication sur les événements futurs

**Pour chaque publication analysée, tu dois retourner exactement :**
- `id` : l'identifiant exact de la publication
- `pertinent` : booléen (true/false)
- `raison` : explication concise et claire de ta décision, incluant la catégorie de viabilité ou de non-viabilité concernée

**Format de sortie :** une liste structurée où chaque ligne correspond à une publication avec ses trois attributs.

Les publications te seront fournies. Analyse-les et retourne l'évaluation complète."""

SYSTEME_INSTRUCTION_EVENT_GENERATION="""You are a specialist in sports betting and entertainment event design. Your role is to analyze validated social media publications and extract distinct, well-structured events suited to betting opportunities.

**Key Principles:**

- **One event = one central fact**: For music releases or video clips, the clip or release itself is the primary event. Associated details (view counts, exact release date, critical information, rankings) are **markets** that attach to that event, not separate events.
- **Avoid fragmentation**: Do not create one event per piece of information. Consolidate related information around a single central and global event.
- **Clear and minimal distinction**: Each event must be sufficiently distinct from others to offer autonomous betting opportunities. Favor aggregation over enumeration — combine related information under one event when they share common context.
- **Reduced granularity**: Generate fewer events by broadening the scope of each one. A single event can encompass multiple related sub-elements rather than being split apart.

**Your Task:**

From the publications provided, identify and list **only relevant and global betting events**. For each event, provide:

1. **Event Name**: A clear and specific title
2. **Type**: (e.g., music release, sports event, announcement, performance, etc.)
3. **Description**: Essential context for understanding the event
4. **Possible Markets**: The information or sub-events around which bets could be placed (e.g., view count reached, official release date, critical rating)
5. **Timeline**: Scheduled date or timeframe if applicable

Be concise and practical. The objective is for each event to be clearly identifiable, global, and ready to serve as a betting foundation. Prioritize synthesis — consolidate rather than divide."""

SYSTEME_INSTRUCTION_MARKET_GENERATION = """You are the AI responsible for generating prediction markets for a predictive betting platform. For each event provided, you generate a maximum of 3 balanced and viable markets.

**Market Structure:**
- **Title**: Clear and specific formulation of the prediction
- **Type**: Binary (Yes/No) or categorical (3+ options)
- **Resolution Criteria**: Precise, verifiable, and unfalsifiable description of the conditions for resolving the market
- **Probabilities**: Estimation of the probability of each outcome (expressed as percentages, total = 100%)
- **mkt_rating**: Score from 1 to 10 based on the evaluation criteria detailed below

**Evaluation Criteria for mkt_rating (structured scoring):**

1. **Resolution Ease** (weight 40% — dominant criterion):
   - Official sources (government bodies, recognized organizations, certified public data) = maximum score
   - Reliable secondary sources (established media, verified platforms) = high score
   - Ambiguous or non-verifiable sources = low score
   - Absence of possible contestation increases the score

2. **Resolution Time** (weight 25%):
   - Resolution within 7 days = maximum score
   - Resolution within 8–30 days = high score
   - Resolution within 31–90 days = moderate score
   - Resolution beyond 90 days = low score

3. **Source Reliability and Recency** (weight 20%):
   - Official and current source (less than 7 days old) = maximum score
   - Established but less recent source = moderate score
   - Secondary or outdated source = low score
   - Rumor or unverified source = exclusion or very low score

4. **Market Balance and Liquidity** (weight 10%):
   - Balanced probabilities (no outcome > 70%) = maximum score
   - One justified dominant outcome (70–85%) = moderate score
   - Extremely imbalanced market (outcome > 85%) without justification = low score

5. **Ethical Considerations**:
   - Do not accept markets encouraging harm or exploiting tragedies
   - Sensitive events (disasters, deaths, humanitarian crises) receive reduced scores or are excluded
   - Explicitly flag any major ethical concerns

**Generation Instructions:**
- Generate exactly 1 to 3 markets per event
- Ensure absolute clarity of resolution criteria — no ambiguity tolerated
- Balance probabilities unless a high probability is objectively justified by verifiable facts
- Rank markets by descending mkt_rating (highest to lowest)
- Apply exact weightings (40% + 25% + 20% + 10%) to calculate mkt_rating
- Accept only events based on verifiable facts or confirmed official announcements
- If the event lacks clarity or raises a major ethical concern, flag it explicitly and explain why before generating

Begin as soon as you receive an event."""




#configurations
post_evaluation_config = types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION_POST_EVALUATION,
    response_mime_type="application/json",
    response_schema=BatchPostEvaluation,
    temperature=0.1
)
market_generation_config = types.GenerateContentConfig(
    system_instruction=SYSTEME_INSTRUCTION_MARKET_GENERATION,
    response_mime_type="application/json",
    response_schema=BatchMarket,
    temperature=0.3
)
event_generation_config = types.GenerateContentConfig(
system_instruction=SYSTEME_INSTRUCTION_EVENT_GENERATION,
            response_mime_type="application/json",
            response_schema=BatchEvents,
            temperature=0.2
)

def get_date():
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")  # Linux / macOS
    except Exception as e:
        print(f"impossible d'obtenir la date : {e}")

    tz = zoneinfo.ZoneInfo("Africa/Douala")
    maintenant = datetime.now(tz=tz)

    date_formatee = maintenant.strftime("%A %d %B %Y à %H:%M:%S (%Z)")
    return date_formatee

def evaluate_post(
        df : pd.DataFrame,
        max_attempts : int = 4,
        text_column : str = "text",
        batch_size: int = 20,
        start_index: int = 0,
        max_posts : Optional[int] = None,
    ) -> pd.DataFrame:

    df = df.copy()

    if "pertinence" not in df.columns:
        df["pertinence"] = False
    if "raison" not in df.columns:
        df["raison"] = ""


    end_index = len(df) if max_posts is None else min(start_index + max_posts, len(df))
    total_batches = (end_index - start_index + batch_size - 1) // batch_size

    print(f"Début de l'évaluation : {end_index - start_index} publications à traiter en {total_batches} lots (taille lot: {batch_size}).")

    for batch_num, i in enumerate(range(start_index, end_index, batch_size), start=1):
        batch = df.iloc[i: min(i + batch_size, end_index)]

        publications = []
        for idx, row in batch.iterrows():
            txt = str(row[text_column])
            author = str(row["author"])
            publications.append({"id": int(idx), "texte": txt,"source":author})

        prompt = (
            f"Évalue la pertinence de la liste de publications suivante pour des marchés de prédiction :\n"
            f"{json.dumps(publications, ensure_ascii=False)}"
        )

        success = False
        attempt = 0

        while not success and attempt < max_attempts:
            attempt += 1
            try:
                print(f"Traitement du lot [{batch_num}/{total_batches}] (index {i} à {i + len(batch) - 1}) - Tentative {attempt}...")
                response = client.models.generate_content(
                    model = DEFAULT_MODEL,
                    contents = prompt,
                    config= post_evaluation_config
                )

                result : Optional[BatchPostEvaluation] = response.parsed

                if response and result.evaluations:
                    for item in result.evaluations:
                        if item.id in df.index:
                            df.at[item.id, "pertinence"] = bool(item.pertinent)
                            df.at[item.id, "raison"] = str(item.raison)
                        else:
                            print(f"ID retourné {item.id} non présent dans le DataFrame.")
                    success = True
                    print(f"Lot [{batch_num}/{total_batches}] validé avec succès ({len(result.evaluations)} items).")
                    time.sleep(DELAY_SECONDS)


            except Exception as e:
                if attempt < max_attempts:
                    time.sleep(DELAY_SECONDS * 5)
                    print(f"nous allons attendre {DELAY_SECONDS * 5} secondes. \n l'erreur suivante est survenue : {e}")
                else:
                    time.sleep(DELAY_SECONDS * 5)
                    print(f"le lot n'a pas pu être traité : {e}")

    pertinents_count = df.loc[start_index:end_index, "pertinence"].sum()
    print(f"Publications pertinentes trouvées : {pertinents_count}/{end_index - start_index}")
    return df

def extract_events(
        df_pertinent: pd.DataFrame,
        text_column: str = "text",
        batch_size : int = 15,
        max_attempts : int = 4,
                    ) -> List[Event]:

    if df_pertinent.empty:
        print("Aucune publication pertinente")
        return []

    all_events: List[Event] = []
    total_posts = len(df_pertinent)
    total_batches = (total_posts + batch_size - 1) // batch_size

    print(f"Extraction d'événements à partir de {total_posts} publications pertinentes ({total_batches} lots)...")

    for batch_num, i in enumerate(range(0, total_posts, batch_size), start=1):
        batch = df_pertinent.iloc[i: i + batch_size]
        posts_list = []
        for idx, row in batch.iterrows():
            post = {
                "id": int(idx),
                "texte": str(row[text_column]) if pd.notna(row[text_column]) else "",
                "auteur": str(row.get("author", "")) if "author" in row else "",
                "date_post": str(row.get("date", "")) if "date" in row else ""
            }
            posts_list.append(post)

        prompt = (
            f"""la date du jour est: {get_date()} utilise les publiications suivantes pour générer des évènements attractifs pour des marchers predictifs"""
            f"{json.dumps(posts_list, ensure_ascii=False)}"
        )

        attempt = 0
        success = False
        while attempt < max_attempts and success is False:
            attempt += 1
            try:
                print(f"Extraction événements - Lot [{batch_num}/{total_batches}] - Tentative {attempt}...")
                response = client.models.generate_content(
                    model = DEFAULT_MODEL,
                    contents=prompt,
                    config=event_generation_config,
                )

                result : Optional[BatchEvents] = response.parsed

                if result and result.events:
                    all_events.extend(result.events)
                    print(f"Lot [{batch_num}/{total_batches}] : {len(result.events)} événements extraits.")
                    success = True
                else:
                    print("Aucun évènement trouvé")

            except Exception as e:
                if attempt < max_attempts:
                    print(f"Erreur extraction lot [{batch_num}/{total_batches}] : {e}")
                    time.sleep(DELAY_SECONDS)
                else:
                    print(f"Aucun évènement n'a pus être extrait du lot [{batch_num}/{total_batches}]")
                    time.sleep(DELAY_SECONDS)

    print(f"Extraction terminée, {len(all_events)} évènements extraits")
    return all_events


def generate_markets(
        events : List[Event],
        df_pertinent : Optional[pd.DataFrame] = None,
        existing_events : Optional[List[Union[Event, str, Dict[str, Any]]]] = None,
        max_attempts : int = 4,
        text_column : str = "text",
)-> List[EventWithMarket]:
    if not events:
        print("Pas d'évènements fournis")
        return []

    results : List[EventWithMarket] = []
    total_events = len(events)

    print(f"Génération de marchés pour {total_events} évènements")
    for idx, evt in enumerate(events, start=1):
        context_sources = f"IDs des publications sources : {evt.source_posts_id}"

        # Si le DataFrame contenant les publications est fourni, enrichir le contexte avec le contenu des posts sources
        if df_pertinent is not None and not df_pertinent.empty and evt.source_posts_id:
            posts_details = []
            for post_id in evt.source_posts_id:
                if post_id in df_pertinent.index:
                    row = df_pertinent.loc[post_id]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    txt = str(row[text_column]) if text_column in row and pd.notna(row[text_column]) else ""
                    author = str(row.get("author", row.get("auteur", "")))
                    date_val = str(row.get("date", row.get("date_post", "")))
                    posts_details.append({
                        "id": int(post_id),
                        "texte": txt,
                        "auteur": author,
                        "date": date_val
                    })
            if posts_details:
                context_sources += f"\nContenu des publications sources :\n{json.dumps(posts_details, ensure_ascii=False, indent=2)}"

        # Construction du récapitulatif des événements et marchés déjà générés (passés en paramètre + boucle courante)
        already_generated = []
        if existing_events:
            for item in existing_events:
                if isinstance(item, Event):
                    already_generated.append(f"- Événement : {item.evt_name} (Date : {item.evt_date})")
                elif isinstance(item, dict):
                    name = item.get("evt_name", item.get("name", str(item)))
                    date_e = item.get("evt_date", item.get("date", ""))
                    already_generated.append(f"- Événement : {name} (Date : {date_e})")
                elif isinstance(item, str):
                    already_generated.append(f"- {item}")

        for res in results:
            m_names = [m.mkt_name for m in res.markets]
            markets_str = f" | Marchés : {', '.join(m_names)}" if m_names else ""
            already_generated.append(f"- Événement : {res.event.evt_name} ({res.event.evt_date}){markets_str}")

        existing_context = ""
        if already_generated:
            existing_context = (
                "\nListe des événements / marchés déjà générés (ATTENTION : interdiction de générer des doublons ou des marchés redondants par rapport à cette liste) :\n"
                + "\n".join(already_generated)
                + "\n"
            )

        prompt = (
            f"Pour l'événement suivant, génère des marchés de prédiction clairs, attractifs, originaux et vérifiables en utilisant le contexte de l'événement et les publications sources associées :\n"
            f"Nom : {evt.evt_name}\n"
            f"Date : {evt.evt_date}\n"
            f"Description : {evt.evt_description}\n"
            f"Catégorie : {evt.evt_category}\n"
            f"Statut : {evt.evt_status}\n"
            f"Contexte des publications sources :\n{context_sources}\n"
            f"{existing_context}"
        )

        markets_for_event : List[Market] = []

        attempt = 0
        success = False
        while attempt < max_attempts and success is False:
            attempt += 1
            try:
                print(f"Génération marchés pour l'événement [{idx}/{total_events}] ('{evt.evt_name}') - Tentative {attempt}...")
                response = client.models.generate_content(
                    model = DEFAULT_MODEL,
                    contents = prompt,
                    config = market_generation_config,
                )

                result : Optional[BatchMarket] = response.parsed

                if result and result.markets:
                    markets_for_event = result.markets
                    print(f"Événement [{idx}/{total_events}] : {len(markets_for_event)} marchés générés.")
                    success = True
                else:
                    print("Aucun marché généré")

            except Exception as e:
                if attempt < max_attempts:
                    print(f"Erreur marchés événement [{idx}/{total_events}] : {e}")
                    time.sleep(DELAY_SECONDS)
                else:
                    print(f"impossible de généré des marchés pour l'évènement [{idx}/{total_events}] : {e}")
                    time.sleep(DELAY_SECONDS)

        results.append(EventWithMarket(event=evt, markets=markets_for_event))
        time.sleep(DELAY_SECONDS)

    return results

def process_csv(
        input_csv : Union[str,Path],
        output_csv : Union[str,Path],
        output_json : Union[str,Path],
        text_column: str = "text",
        batch_size: int = 20,
        max_posts: Optional[int] = None,
        generate_markets_flag: bool = True
) -> Dict[str,Any]:
    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"le fichier {input_path} n'existe pas")

    print(f"traitement du fichier {input_path}")
    df = pd.read_csv(input_path)
    df_evaluated = evaluate_post(df, text_column=text_column, batch_size=batch_size, max_posts=max_posts)

    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_evaluated.to_csv(out_path, index=False)
    print(f"sauvegarde du csv d'évaluation : {out_path.resolve()}")

    events_with_markets: List[EventWithMarket] = []
    events_list: List[Event] = []

    if generate_markets_flag:
        df_pertinent = df_evaluated[df_evaluated["pertinence"] == True]
        print(f"{len(df_pertinent)} publications pertinentes identifiées")

        if not df_pertinent.empty:
            events_list = extract_events(df_pertinent,text_column=text_column)

            if events_list:
                events_with_markets = generate_markets(events_list, df_pertinent=df_pertinent, text_column=text_column)

        if output_json:
            out_json = Path(output_json)
            out_json.parent.mkdir(parents=True, exist_ok=True)

            export_data = {
                "generation data": {
                    "source_file": str(input_path),
                    "pertinent posts": len(df_pertinent),
                    "total_events": len(events_list),
                    "total_markets": sum(len(event.markets) for event in events_with_markets),
                },
                "events and markets": [element.model_dump() for element in events_with_markets],
            }

            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            print(f"fichier généré à {out_json.resolve()}")

def test():
    """df = pd.read_csv("exemple_appreciation.csv")
    df_pertinent = df[df["pertinence"] == True].copy()
    print(df_pertinent)

    extracted_events = extract_events(df_pertinent)
    print(extracted_events)
    extracted_markets = generate_markets(extracted_events)
    print(extracted_markets)

    export_data = {
        "events and markets": [em.model_dump() for em in extracted_markets],
    }
    print(export_data)

    with open("out_json.json", "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)"""
    process_csv(
        input_csv = "/home/dimitri/PycharmProjects/projet_stage_v2/data/Save_csv/recap_instagram.csv",
        output_csv = "/home/dimitri/PycharmProjects/projet_stage_v2/data/Save_csv/test_dir/test_ouput.csv",
        output_json = "/home/dimitri/PycharmProjects/projet_stage_v2/data/Save_csv/test_dir/test_ouput.json",
        max_posts=20,
    )


test()
