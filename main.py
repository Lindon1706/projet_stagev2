"""import pandas as pd
from pathlib import Path
from modules.storage import convert_to_csv

name_file = "Data_Canal2Or"
dossier_insta = Path("./data/Canal2Or/posts_instagram")
summarized_insta_data = convert_to_csv(dossier_insta,"posts_instagram")
summarized_insta_data.to_csv(f"./data/Save_csv/{name_file}.csv",index=False)"""
#print(f"vos données ont été condensées dans le fichier data/Save_csv/"""{name_file}.csv")



import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

with open("data/Save_csv/recap_instagram.csv", "r", encoding="utf-8") as f:
    csv_data = f.read()

# 1. Définition de la fonction/outil
def give_info() -> str:
    return f"voici les données que nous avons pu extraire{csv_data}"


#Création d'une session Chat
chat = client.chats.create(
    model="gemini-3.5-flash",
    config=types.GenerateContentConfig(
        tools=[give_info]
    )
)


print("Envoi de la requête...")
response = chat.send_message(f"extrait des évènements de {csv_data} et des marchers style polymarket au format Json")

#Écriture du résultat final dans un fichier
nom_fichier = "markets.txt"
with open(nom_fichier, "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"Réponse enregistrée dans '{nom_fichier}'.")
with open("data/Save_csv/test_dir/villes.json", "w", encoding="utf-8") as f:
    f.write(response.text)

if 0:
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            f"Voici un fichier CSV :\n```csv\n{csv_data}\n```",
            f"en respectant les contraintes de {content} avec ce fichier imagine que tu es l'IA d'un site de pari et essaie d'extraire des évènements interessants pour des paris sans toutefois formuler demarcher et spécifie des critères de résolution "
                ]
    )

    print(response.text)
if 0:
    from modules.recap_instagram_posts import compile_instagram_posts_to_csv

    # Consolider des dossiers spécifiques
    dossiers = ["FallyIpupa", "musicinafrica","tanzaniacharts","AfricanMusic","Afrobeats","EastAfricanMusic","AfricanRap","musicinafricaofficial","billboardafrica","rollingstoneafrica","mood_du_rap_ivoire","showbuzz_tv","classic105kenya","sondubledmedia","afrimma"]
    records = compile_instagram_posts_to_csv(
        folders=dossiers,
        data_dir="data",
        output_csv="data/Save_csv/recap_instagram.csv"
    )

