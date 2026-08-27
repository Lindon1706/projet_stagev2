import requests
from bs4 import BeautifulSoup
from pprint import pprint
import pandas as pd

if __name__ == "__main__":
    url = "https://www.mboaticket.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    events_box = soup.find_all("div", class_ = "ev-body")
    event_list = [event.find("h3", class_ = "ev-title").text.strip() for event in events_box]
    event_info = [event.find_all("span", class_ = "truncate") for event in events_box]
    event_date = [event[1].text.strip() for event in event_info]
    event_organizer = [event[0].text.strip() for event in event_info]
    event_location = [event[2].text.strip() for event in event_info]

    event_data = list(zip(event_list, event_date, event_organizer, event_location))
    df = pd.DataFrame(event_data, columns=["Event", "Date", "Organizer", "Location"])

    mois_fr = {
        "Janv": "01",
        "Jan": "01",
        "Fév": "02",
        "Fev": "02",
        "Mars": "03",
        "Mar": "03",
        "Avr": "04",
        "Mai": "05",
        "Jui": "06",
        "Juin": "06",
        "Juil": "07",
        "Jul": "07",
        "Aoû": "08",
        "Aou": "08",
        "Sept": "09",
        "Sep": "09",
        "Oct": "10",
        "Nov": "11",
        "Déc": "12",
        "Dec": "12",
    }

    dates_temp = df["Date"].str.strip().str.replace("h", ":")
    import instaloader
    import re

    def get_details(code_post : str):
        L = instaloader.Instaloader()
        post = instaloader.Post.from_shortcode(L.context, code_post)
        return {
            "author": post.owner_username,
            "date": post.date_utc,
            "likes":post.likes,
            "texte":post.caption,
        }

    def extract_post_code(post_url : str):
        return re.search(r'/p/([^/]+)', post_url).group(1)

    for fr, num in mois_fr.items():
        dates_temp = dates_temp.str.replace(fr, num, regex=False)

    df["date_cleaned"] = pd.to_datetime(dates_temp, format="%d %m %Y, %H:%M", errors="coerce")

    df.to_csv("events_cleaned.csv", index=False)