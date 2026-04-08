from bs4 import BeautifulSoup

def parse_anime(html: str):
    soup = BeautifulSoup(html, "html.parser")

    title_s = soup.select_one("#titreOeuvre")
    synopsis_s= soup.select_one("p.text-sm")
    
    if title_s is None or  synopsis_s is None:
        return None
    
    title=title_s.text.strip()
    synopsis=synopsis_s.text.strip()

    genres = [
        g.text.strip()
        for g in soup.select("a.text-sm.text-gray-300")
    ]

    return {
        "title": title,
        "synopsis": synopsis,
        "genres": genres
    }


def parse_seasons(html: str):
    soup = BeautifulSoup(html, "html.parser")

    seasons = []
    for a in soup.select("a[href*='saison']"):
        seasons.append({
            "name": a["href"].strip("/")[0],
            "url": a["href"],
            "type":"season",
        })

    return seasons


def parse_scan(html: str):
    soup = BeautifulSoup(html, "html.parser")


    scans = []
    for a in soup.select("a[href*='scan']"):
        scans.append({
            "name": a["href"].strip("/")[0],
            "url": a["href"],
            "type":"scan",
        })
        
    return scans
        
        
def parse_film(html: str):
    soup = BeautifulSoup(html, "html.parser")


    films = []
    for a in soup.select("a[href*='film']"):
        films.append({
            "name": a["href"].strip("/")[0],
            "url": a["href"],
            "type":"film",
        })
        
    return films







