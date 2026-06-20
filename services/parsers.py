"""
Parsers HTML pour anime-sama.to.

Sélecteurs CSS clés validés sur le site :
  Catalogue page (#sousBlocMiddle inner HTML) :
    div.oeuvre-right h1              → nom
    #titreAlter                      → titre alternatif
    #synopsisText                    → synopsis
    .genre-pill                      → genres
    table.info-table td.lbl/td.val   → métadonnées (état, année, studio…)
    a[img#imgOeuvre]                 → cartes de contenus (saisons/films/scans)
      href = /catalogue/{slug}/{contenu_slug}/{lang}/
      img#imgOeuvre src = image
      div = nom du contenu ("Saison 1 VOSTFR", "Film 1 VF"…)

  Recherche (#asn-result-desktop inner HTML) :
    a.asn-search-result              → item
      href = /catalogue/{slug}/
      img.asn-search-result-img      → image
      h3.asn-search-result-title     → titre

  Catalogue liste (/catalogue/?…) :
    a[href^="/catalogue/"][img]      → cartes de la liste
      h3                            → titre
      img                           → image

  Planning (/planning/) :
    h2                              → jour de la semaine
    p (après h2)                    → date (ex: "15/06")
    a[href*="/catalogue/"]          → entrée planning
      h3                            → titre anime
      p (contenant "h")             → heure (ex: "12h00")
      p (dernier)                   → saison info
"""

from __future__ import annotations
import re
from bs4 import BeautifulSoup
from typing import Optional
from params import BASE_SAMA_URL
from models.catalogue import (
    Catalogue, Etat, TypeContenu,
    Saison, Film, Scan,
)

_LANG_CODES = {
    "vostfr", "vf", "vf1", "vf2", "vo", "va",
    "vqc", "vqc1", "van", "var", "vkr", "vcn",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _abs(url: Optional[str]) -> Optional[str]:
    if url and url.startswith("/"):
        return BASE_SAMA_URL.rstrip("/") + url
    return url


def _abs_content(url: str, cat_slug: str = "") -> str:
    """
    Convertit n'importe quel href en URL absolue.
    Gère les 3 cas que produit anime-sama :
      /catalogue/naruto/saison1/vostfr/  → absolu (leading /)
      https://anime-sama.to/…            → déjà absolu
      saison1/vostfr                     → relatif à /catalogue/{cat_slug}/
    """
    if not url:
        return ""
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return BASE_SAMA_URL.rstrip("/") + url
    # URL relative à /catalogue/{cat_slug}/
    if cat_slug:
        return f"{BASE_SAMA_URL}catalogue/{cat_slug}/{url.strip('/')}/"
    return url


def _parse_content_url(url: str, cat_slug: str = "") -> tuple[str, str, Optional[str]]:
    """
    /catalogue/naruto/saison1/vostfr/  →  ("naruto", "saison1", "vostfr")
    /catalogue/naruto/scan/             →  ("naruto", "scan",    None)
    saison1/vostfr                      →  (cat_slug, "saison1", "vostfr")  ← URL relative
    """
    parts = [p for p in url.rstrip("/").split("/") if p]
    try:
        idx = parts.index("catalogue")
        c_slug    = parts[idx + 1] if idx + 1 < len(parts) else ""
        cont_slug = parts[idx + 2] if idx + 2 < len(parts) else ""
        lang_part = parts[idx + 3] if idx + 3 < len(parts) else ""
        lang      = lang_part.lower() if lang_part.lower() in _LANG_CODES else None
        return c_slug, cont_slug, lang
    except ValueError:
        # URL relative : [cont_slug, lang?]
        cont_slug = parts[0] if parts else ""
        lang_part = parts[1] if len(parts) > 1 else ""
        lang      = lang_part.lower() if lang_part.lower() in _LANG_CODES else None
        return cat_slug, cont_slug, lang


def _is_saison(name: str, slug: str) -> bool:
    n = name.lower()
    return any(k in n for k in ("saison", "season", "sans fillers", "kai")) or \
           any(k in slug for k in ("saison", "season"))


def _is_film(name: str, slug: str) -> bool:
    n = name.lower()
    return "film" in n or "movie" in n or "film" in slug or "movie" in slug


def _is_scan(name: str, slug: str) -> bool:
    n = name.lower()
    return "scan" in n or "manga" in n or "scan" in slug or "manga" in slug


class Parser:

    # ------------------------------------------------------------------
    # Catalogue complet (depuis #sousBlocMiddle)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_catalogue(html: str, slug: str = "") -> Catalogue:
        """
        Parse le HTML interne de #sousBlocMiddle.
        `slug` est passé pour construire les URLs et identifier les contenus.
        Retourne un Catalogue avec saisons/films/scans (sans épisodes).
        """
        soup = BeautifulSoup(html, "html.parser")
        root = soup.select_one("div.oeuvre-right")
        if root is None:
            raise ValueError("div.oeuvre-right introuvable dans le HTML fourni")

        # Nom
        h1 = root.select_one("h1")
        nom = h1.get_text(strip=True) if h1 else "Inconnu"

        # Titre alternatif
        alt_el = root.select_one("#titreAlter")
        titre_alt = alt_el.get_text(strip=True) if alt_el else None

        # Synopsis
        syn_el = root.select_one("#synopsisText")
        synopsis = syn_el.get_text("\n", strip=True) if syn_el else None

        # Image principale (première img dans le bloc oeuvre-left si présente)
        img_el = soup.select_one("div.oeuvre-left img, img#imgOeuvreMain, .img-catalogue")
        image = _abs(img_el.get("src")) if img_el else None

        # Genres — cherche le premier div.oeuvre-section qui contient des .genre-pill
        # (le premier oeuvre-section est le synopsis, le second les genres)
        genres: list[str] = []
        for section in root.select("div.oeuvre-section"):
            pills = section.select(".genre-pill")
            if pills:
                genres = [p.get_text(strip=True) for p in pills]
                break
        if not genres:
            genres = [g.get_text(strip=True) for g in root.select(".genre-pill")]

        # Métadonnées — structure réelle anime-sama.to :
        #   <span class="info-lbl">État</span><span class="info-val">Terminé</span>
        #   dans un div.info-card
        metadata: dict = {}

        # Méthode principale : span.info-lbl / span.info-val
        lbl_els = soup.select("span.info-lbl")
        val_els = soup.select("span.info-val")
        for lbl_el, val_el in zip(lbl_els, val_els):
            lbl = lbl_el.get_text(strip=True).replace(":", "").strip().lower()
            val = val_el.get_text(strip=True)
            if lbl and val:
                metadata[lbl] = val

        # Fallback : table.info-table td.lbl / td.val (ancienne structure éventuelle)
        if not metadata:
            for row in root.select("table.info-table tr, table tr"):
                lbl_cells = row.select("td.lbl, th")
                val_cells = row.select("td.val, td:not(.lbl)")
                for lbl_c, val_c in zip(lbl_cells, val_cells):
                    lbl = lbl_c.get_text(strip=True).replace(":", "").strip().lower()
                    val = val_c.get_text(strip=True)
                    if lbl and val and lbl != val:
                        metadata[lbl] = val

        # Fallback ultime : pattern "Label : Valeur" dans les <p> et <li>
        if not metadata:
            for el in root.select("p, li, div.info-item"):
                txt = el.get_text(strip=True)
                if ":" in txt and len(txt) < 100:
                    parts = txt.split(":", 1)
                    if len(parts) == 2:
                        lbl = parts[0].strip().lower()
                        val = parts[1].strip()
                        if lbl and val and len(lbl) < 25:
                            metadata.setdefault(lbl, val)

        # État — cherche les clés communes, puis texte libre
        _TERMINE  = {"terminé", "termine", "finished", "completed", "ended"}
        _EN_COURS = {"en cours", "ongoing", "airing", "en diffusion"}
        _ABANDONNE = {"abandonné", "abandonne", "cancelled", "canceled", "dropped"}

        def _detect_etat(text: str) -> Optional[Etat]:
            t = text.lower()
            if any(w in t for w in _TERMINE):
                return Etat.TERMINE
            if any(w in t for w in _EN_COURS):
                return Etat.EN_COURS
            if any(w in t for w in _ABANDONNE):
                return Etat.ABANDONNE
            return None

        etat = Etat.EN_COURS
        for key in ("état", "etat", "statut", "status", "diffusion"):
            if key in metadata:
                detected = _detect_etat(metadata[key])
                if detected is not None:
                    etat = detected
                    break

        # Contenus
        saisons, films, scans, langues_set = Parser._parse_contenus_cards(html, cat_slug=slug)

        # Type global du catalogue
        if scans and not saisons and not films:
            type_contenu = TypeContenu.SCAN
        elif films and not saisons and not scans:
            type_contenu = TypeContenu.FILM
        else:
            type_contenu = TypeContenu.ANIME

        return Catalogue(
            slug=slug,
            url=_abs(f"/catalogue/{slug}/") or "",
            nom=nom,
            titre_alternatif=titre_alt,
            synopsis=synopsis,
            image=image,
            genres=genres,
            langues=sorted(langues_set),
            etat=etat,
            type_contenu=type_contenu,
            saisons=saisons,
            films=films,
            scans=scans,
            metadata=metadata,
        )

    @staticmethod
    def _parse_contenus_cards(html: str, cat_slug: str = "") -> tuple[list[Saison], list[Film], list[Scan], set]:
        """
        Parcourt les cartes <a href="…"><img id="imgOeuvre">…</a>
        et retourne (saisons, films, scans, langues_disponibles).
        Les hrefs peuvent être absolus (/catalogue/…) ou relatifs (saison1/vostfr).
        """
        soup = BeautifulSoup(html, "html.parser")
        cards = [a for a in soup.find_all("a") if a.select_one("img#imgOeuvre")]

        saisons: list[Saison] = []
        films:   list[Film]   = []
        scans:   list[Scan]   = []
        langues: set[str]     = set()

        for card in cards:
            div = card.select_one("div")
            name = div.get_text(strip=True) if div else card.get_text(strip=True)
            raw_url = card.get("href", "")
            url = _abs_content(raw_url, cat_slug)
            img = _abs(card.select_one("img#imgOeuvre").get("src", ""))

            _, cont_slug, lang = _parse_content_url(raw_url, cat_slug)
            if lang:
                langues.add(lang)

            if _is_saison(name, cont_slug):
                saisons.append(Saison(
                    nom=name,
                    slug=cont_slug,
                    lang=lang or "vostfr",
                    url=url,
                    image=img,
                ))
            elif _is_film(name, cont_slug):
                films.append(Film(
                    nom=name,
                    slug=cont_slug,
                    lang=lang or "vostfr",
                    url=url,
                    image=img,
                ))
            elif _is_scan(name, cont_slug):
                scans.append(Scan(
                    nom=name,
                    slug=cont_slug,
                    lang=lang,
                    url=url,
                    image=img,
                ))

        return saisons, films, scans, langues

    # ------------------------------------------------------------------
    # Chapitres d'un scan (/catalogue/{slug}/scan/…)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_scan_chapitres(html: str, base_url: str = "") -> list[dict]:
        """
        Parse une page de scan pour extraire la liste des chapitres.
        Deux structures possibles sur anime-sama :
          1. Select #selectEpisodes (même mécanique que les pages épisodes)
          2. Liste de liens <a> vers les chapitres
        Retourne [{numero, titre, url}] trié par numéro croissant.
        """
        soup = BeautifulSoup(html, "html.parser")
        chapitres: list[dict] = []

        # --- Cas 1 : select d'épisodes/chapitres ---
        select = soup.select_one("#selectEpisodes")
        if select:
            for opt in select.select("option"):
                txt     = opt.get_text(strip=True)
                val     = opt.get("value", "")
                num_m   = re.search(r"(\d+(?:\.\d+)?)", txt)
                num     = float(num_m.group(1)) if num_m else 0.0
                url     = _abs(val) if val.startswith("/") else (
                          f"{base_url.rstrip('/')}/{val.strip('/')}" if val else base_url)
                chapitres.append({"numero": num, "titre": txt, "url": url})
            return chapitres

        # --- Cas 2 : liens de chapitres ---
        seen: set[float] = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            txt  = a.get_text(strip=True)
            if not txt or len(txt) > 80:
                continue

            # Reconnaître "Chapitre 12", "Chapter 12.5", "Ch.3", "12", …
            num_m = re.search(
                r"(?:chapitre|chapter|chap\.?|ch\.?)\s*(\d+(?:[.,]\d+)?)",
                txt, re.I
            ) or re.search(r"^(\d+(?:[.,]\d+)?)\s*[–-]", txt) \
              or re.search(r"^(\d+(?:[.,]\d+)?)$", txt.strip())

            if not num_m:
                continue

            num = float(num_m.group(1).replace(",", "."))
            if num in seen:
                continue
            seen.add(num)

            url = _abs(href) if href.startswith("/") else (
                  href if href.startswith("http") else
                  f"{base_url.rstrip('/')}/{href.strip('/')}")

            chapitres.append({"numero": num, "titre": txt, "url": url})

        chapitres.sort(key=lambda c: c["numero"])
        return chapitres

    # ------------------------------------------------------------------
    # Résultats de recherche (barre de recherche du site)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_resultats_recherche(html: str) -> list[dict]:
        """
        Parse #asn-result-desktop inner HTML.
        Retourne [ { title, url, image, slug } ]
        """
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for item in soup.select("a.asn-search-result"):
            try:
                raw_url = item.get("href", "")
                parts = [p for p in raw_url.rstrip("/").split("/") if p]
                slug = parts[-1] if parts else ""
                img_tag   = item.select_one("img.asn-search-result-img")
                title_tag = item.select_one("h3.asn-search-result-title")
                if not title_tag:
                    continue
                results.append({
                    "title": title_tag.get_text(strip=True),
                    "url":   _abs(raw_url) or raw_url,
                    "image": _abs(img_tag.get("src", "")) if img_tag else None,
                    "slug":  slug,
                })
            except Exception:
                continue
        return results

    # ------------------------------------------------------------------
    # Liste paginée du catalogue (/catalogue/?…)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_liste_catalogue(html: str) -> list[dict]:
        """
        Parse la page liste du catalogue anime-sama.
        Retourne [ { title, slug, url, image, genres, types, langues } ]
        """
        soup = BeautifulSoup(html, "html.parser")
        results = []
        seen: set[str] = set()

        for card in soup.select("a[href]"):
            href = card.get("href", "")
            parts = [p for p in href.rstrip("/").split("/") if p]
            # Garder seulement /catalogue/{slug}/ (profondeur 2)
            if len(parts) != 2 or parts[0] != "catalogue":
                continue
            slug = parts[1]
            if slug in seen:
                continue
            seen.add(slug)

            img_tag   = card.select_one("img")
            title_tag = card.select_one("h2, h3, .titre, [class*='title']")
            title = title_tag.get_text(strip=True) if title_tag else slug

            genres_tags = card.select(".genre-pill, .genre, [class*='genre']")
            genres = [g.get_text(strip=True) for g in genres_tags]

            results.append({
                "title":  title,
                "slug":   slug,
                "url":    _abs(href),
                "image":  _abs(img_tag.get("src", "")) if img_tag else None,
                "genres": genres,
            })

        return results

    # ------------------------------------------------------------------
    # Genres disponibles depuis /catalogue/
    # ------------------------------------------------------------------

    @staticmethod
    def parse_genres_from_catalogue(html: str) -> list[str]:
        """
        Extrait tous les genres disponibles depuis la page /catalogue/.

        Structure réelle anime-sama.to (validée 2026-06) :
          #genreList > label.filter-checkbox-item > input.filter-checkbox[name="genre[]"][value="..."]

        Stratégies dans l'ordre :
          0. #genreList input.filter-checkbox → attribut value  (sélecteur validé)
          1. Tout input[name*="genre"] → attribut value (fallback)
          2. .genre-pill des cartes catalogue (fallback ancien)
        """
        soup = BeautifulSoup(html, "html.parser")
        genres: set[str] = set()

        # Stratégie 0 — sélecteur validé : #genreList input.filter-checkbox
        genre_list = soup.select("#genreList input.filter-checkbox")
        for inp in genre_list:
            val = inp.get("value", "").strip()
            if val and len(val) >= 2:
                genres.add(val)

        # Stratégie 1 — tout input dont le name contient "genre"
        if len(genres) < 5:
            for inp in soup.select("input[type='checkbox'], input[type='radio']"):
                name = inp.get("name", "").lower()
                if "genre" in name:
                    val = inp.get("value", "").strip()
                    if val and val.lower() not in ("", "0"):
                        genres.add(val)

        # Stratégie 2 — .genre-pill des cartes catalogue
        if len(genres) < 5:
            for pill in soup.select(".genre-pill"):
                txt = pill.get_text(strip=True)
                if txt and 2 <= len(txt) <= 60:
                    genres.add(txt)

        return sorted(genres)

    # ------------------------------------------------------------------
    # Planning (/planning/)  —  HTML statique
    # ------------------------------------------------------------------

    @staticmethod
    def parse_planning(html: str) -> list[dict]:
        """
        Parse la page planning anime-sama.
        Retourne une liste de jours avec leurs animés :
        [
          {
            "jour": "Lundi",
            "date": "15/06",
            "animes": [
              { "titre", "slug", "url", "image", "heure", "saison", "lang" }
            ]
          },
          …,
          {
            "jour": "Sans jour fixe",
            "date": null,
            "animes": […]
          }
        ]
        """
        soup = BeautifulSoup(html, "html.parser")
        planning = []
        current_day: dict | None = None

        for el in soup.find_all(["h2", "p", "a"]):
            # Nouveau jour
            if el.name == "h2":
                current_day = {
                    "jour":   el.get_text(strip=True),
                    "date":   None,
                    "animes": [],
                }
                planning.append(current_day)

            # Date du jour (premier <p> après un <h2>)
            elif el.name == "p" and current_day and current_day["date"] is None:
                text = el.get_text(strip=True)
                # La date ressemble à "15/06" ou "15/06/2026"
                if "/" in text and len(text) <= 10:
                    current_day["date"] = text

            # Entrée d'animé
            elif el.name == "a" and current_day:
                href = el.get("href", "")
                if "/catalogue/" not in href:
                    continue

                _, _, lang = _parse_content_url(href)
                cat_slug = [p for p in href.rstrip("/").split("/") if p]
                cat_slug = cat_slug[1] if len(cat_slug) > 1 else ""

                img_tag   = el.select_one("img")
                title_tag = el.select_one("h3, h2, .titre")
                title = title_tag.get_text(strip=True) if title_tag else cat_slug

                # Heure : paragraphe contenant "h" suivi de chiffres (12h00)
                heure = None
                saison_info = None
                for p in el.select("p"):
                    txt = p.get_text(strip=True)
                    if "h" in txt and any(c.isdigit() for c in txt) and len(txt) <= 8:
                        heure = txt
                    elif txt and heure is not None:
                        saison_info = txt

                current_day["animes"].append({
                    "titre":       title,
                    "slug":        cat_slug,
                    "url":         _abs(f"/catalogue/{cat_slug}/") or href,
                    "url_saison":  _abs(href),
                    "image":       _abs(img_tag.get("src", "")) if img_tag else None,
                    "heure":       heure,
                    "saison_info": saison_info,
                    "lang":        lang or "vostfr",
                })

        return planning
