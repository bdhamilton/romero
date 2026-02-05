import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_homilies_from_index():
    # Get the HTML for the homilies index
    index_url = "https://www.romerotrust.org.uk/homilies-and-writing/homilies/"
    response = requests.get(index_url)

    # Parse index for occasion, title, date, audio presence, and biblical passages
    soup = BeautifulSoup(response.content, 'html.parser')
    homily_occasions = soup.find_all("div", class_="field-name-field-homily-occasion")

    homilies = []
    for occasion in homily_occasions:
        # Get data blocks for this homily
        title_block = occasion.find_next_sibling("div", class_="views-field-title")
        date_block = occasion.find_next_sibling("div", class_="field-name-field-date")

        # References might or might not exist; look for a <p> before the next occasion.
        references_text = ""
        for sib in date_block.next_siblings:
            name = getattr(sib, "name", None)
            classes = (sib.get("class") or []) if name else []
            if name == "div" and "field-name-field-homily-occasion" in classes:
                break  # reached the next homily; stop
            if name == "p":
                references_text = sib.get_text(" ", strip=True).replace("\xa0", " ")
                break

        # Parse needed fields
        date_obj = datetime.strptime(date_block.get_text(strip=True), "%d %B %Y").date()
        has_audio = "(+AUDIO)" in references_text or "AUDIO" in references_text
        passages_source = references_text.split(")", 1)[1].strip() if ")" in references_text else references_text
        passages = [p.strip() for p in passages_source.split(";") if p.strip()]

        homilies.append({
            "occasion": occasion.get_text(strip=True),
            "title": title_block.get_text(strip=True),
            "url": title_block.a["href"],
            "date": date_obj.isoformat(),
            "has_audio": has_audio,
            "passages": passages,
        })

    return homilies

def add_pdf_urls(homilies):
    # Look at each homily

    # Fetch 