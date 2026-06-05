
from bs4 import BeautifulSoup
from typing import Any, Optional, List
from core.http_client import http_client
from models.catalogue import Catalogue, Etat
from models.contents import (
    Content, Season, Episode, Film, Scan, Anime,MangaChapitre, MangaImage, TypeContent
)

from utils.fonction import build_video_url

class Parser:
    @staticmethod
    def parse_season(html)->Season:
        
        pass
    
    
    
    @staticmethod
    def parse_contenus_cards(html) -> list[Content]:
        contenus = []
        root = BeautifulSoup(html, "html.parser")

        # Sélection fiable des cartes
        cards = [a for a in root.find_all("a") if a.select_one("img#imgOeuvre")]

        for card in cards:
            name = card.select_one("div").get_text(strip=True)
            url = card.get("href")
            img = card.select_one("img#imgOeuvre").get("src")

            name_lower = name.lower()

            # SAISON
            if "saison" in name_lower or "season" in name_lower:
                contenus.append(
                    Season(
                        name=name,
                        type=TypeContent.SEASON,
                        metadata={"url": url, "image": img},
                        data=[]
                    )
                )

            # FILM
            elif "film" in name_lower:
                contenus.append(
                    Film(
                        name=name,
                        type=TypeContent.FILM,
                        metadata={"url": url, "image": img},
                        data=[]
                    )
                )

            # KAI / SANS FILLERS / AUTRES VERSIONS
            elif "kai" in name_lower or "sans fillers" or"fillers" in name_lower:
                contenus.append(
                    Anime(
                        name=name,
                        type=TypeContent.ANIME,
                        metadata={"url": url, "image": img},
                        seasons=[]
                    )
                )
            elif "scans" in name_lower:
                contenus.append(
                    MangaChapitre(
                        name=name,
                        images=[],
                        metadata={"url": url, "image": img}
                    )
                )

            # AUTRE
            else:
                contenus.append(
                    Content(
                        name=name,
                        type=TypeContent.AUTRE,
                        metadata={"url": url, "image": img}
                    )
                )

        return contenus




    @staticmethod
    def parse_catalogue(html: str) -> Catalogue:
        soup = BeautifulSoup(html, "html.parser")
        root = soup.select_one("div.oeuvre-right")

        # --- Titre principal ---
        name = root.select_one("h1").get_text(strip=True)

        # --- Titre alternatif ---
        titre_alter_el = root.select_one("#titreAlter")
        titre_alter = titre_alter_el.get_text(strip=True) if titre_alter_el else None

        # --- Synopsis ---
        synopsis_el = root.select_one("#synopsisText")
        synopsis = synopsis_el.get_text("\n", strip=True) if synopsis_el else None

        # --- Genres ---
        genres = [g.get_text(strip=True) for g in root.select(".genre-pill")]

        # --- Métadonnées ---
        metadata = {}
        for row in root.select("table.info-table tr"):
            labels = [l.get_text(strip=True).replace(":", "").strip().lower() for l in row.select("td.lbl")]
            values = [v.get_text(strip=True) for v in row.select("td.val")]
            for label, value in zip(labels, values):
                metadata[label] = value

        # --- État ---
        etat_str = metadata.get("état", "").lower()
        if "terminé" in etat_str:
            etat = Etat.TERMINE
        elif "cours" in etat_str:
            etat = Etat.EN_COURS
        elif "abandonné" in etat_str:
            etat = Etat.ABONNDONNE
        else:
            etat = Etat.EN_COURS


        # --- Création du modèle Catalogue ---
        catalogue= Catalogue(
            name=name,
            synopsis=synopsis,
            aperçu=titre_alter,
            genres=genres,
            etat=etat,
            contenus=Parser.parse_contenus_cards(html),
            metadata=metadata
        )
        
        if not catalogue.contenus is None:
            for i in range(len(catalogue.contenus)):
        
                if catalogue.contenus[i].type==TypeContent.SEASON:
                    pass
            
       
        return catalogue

    @staticmethod
    def parse_anime_search_url_catalogue(html: str) -> list[dict[str, any]]:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Chaque résultat est un <a class="asn-search-result">
        items = soup.select("a.asn-search-result")

        for item in items:
            try:
                url = item.get("href")
                img = item.select_one("img.asn-search-result-img").get("src")
                title = item.select_one("h3.asn-search-result-title").get_text(strip=True)

                results.append({
                    "title": title,
                    "url": url,
                    "image": img
                })
            except Exception:
                continue

        return results


    
    
    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
            
    @staticmethod        
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







