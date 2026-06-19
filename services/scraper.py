"""
Scraper anime-sama.to — sync_playwright dans ThreadPoolExecutor.

Pourquoi sync_playwright ?
  Sur Windows, uvicorn utilise WindowsSelectorEventLoop qui ne supporte pas
  asyncio.create_subprocess_exec (utilisé par async_playwright).
  sync_playwright utilise subprocess.Popen standard → compatible Windows.
  Les fonctions publiques sont async via loop.run_in_executor().

Pourquoi ThreadPoolExecutor(max_workers=2) ?
  Chromium consomme ~300 Mo RAM par instance. 2 workers max évite la saturation.
"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import urlencode

import httpx
from playwright.sync_api import sync_playwright

from params import BASE_SAMA_URL, PLAYWRIGHT_PROXY
from utils.logger import logger
from services.parsers import Parser
from models.catalogue import Catalogue

_executor = ThreadPoolExecutor(max_workers=2)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _open_page(p) -> tuple:
    proxy = {"server": PLAYWRIGHT_PROXY} if PLAYWRIGHT_PROXY else None
    browser = p.chromium.launch(headless=True, proxy=proxy)
    ctx = browser.new_context(user_agent=_UA, ignore_https_errors=True)
    return browser, ctx.new_page()


_BLOCK_KEYWORDS = ("filtre web", "fortigate", "intrusion prevention", "access denied",
                   "your request has been blocked", "page bloquée")

def _is_blocked(page) -> bool:
    """Retourne True si la page est une page de blocage réseau (FortiGuard, etc.)."""
    title = (page.title() or "").lower()
    return any(k in title for k in _BLOCK_KEYWORDS)


def _debug_page_state(page, label: str) -> None:
    """Log l'état réel de la page pour diagnostiquer les échecs."""
    try:
        title = page.title()
        url   = page.url
        ids   = page.evaluate(
            "() => Array.from(document.querySelectorAll('[id]')).map(e=>e.id).filter(Boolean).slice(0,20)"
        )
        logger.warning(f"[debug:{label}] title={title!r} url={url!r} ids={ids}")
    except Exception as e:
        logger.warning(f"[debug:{label}] impossible d'inspecter la page : {e}")


# ---------------------------------------------------------------------------
# Recherche via barre de recherche (Playwright)
# ---------------------------------------------------------------------------

def _search_sync(query: str) -> list[dict]:
    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)
            page.goto(BASE_SAMA_URL, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_selector(
                "div.asn-desktop-search input[name='search_text']", timeout=10000
            )
            page.fill("div.asn-desktop-search input[name='search_text']", query)
            page.wait_for_timeout(1500)
            html = page.locator("#asn-result-desktop").inner_html()
            browser.close()
            return Parser.parse_resultats_recherche(html)
    except Exception:
        logger.exception(f"Erreur recherche barre {query!r}")
        return []


# ---------------------------------------------------------------------------
# Catalogue /catalogue/?q=…&type=…  (Playwright — JS requis pour les filtres)
# ---------------------------------------------------------------------------

def _search_catalogue_site_sync(
    q: Optional[str] = None,
    type_contenu: Optional[str] = None,
    lang: Optional[str] = None,
    statut: Optional[str] = None,
    genres: Optional[list[str]] = None,
    page_num: int = 1,
) -> list[dict]:
    """
    Scrape /catalogue/ avec les filtres URL.
    Paramètres :
      q           → ?q=naruto
      type_contenu → ?type=anime|scans|film|autres
      lang        → ?lang=vostfr|vf|vastfr
      statut      → ?statut=en-cours|termine
      genres      → ?genres=action,aventure  (multiples séparés par virgule)
      page_num    → ?page=N
    """
    params: dict = {"page": page_num}
    if q:           params["q"]      = q
    if type_contenu: params["type"]  = type_contenu
    if lang:        params["lang"]   = lang
    if statut:      params["statut"] = statut
    if genres:      params["genres"] = ",".join(genres)

    url = f"{BASE_SAMA_URL}catalogue/?{urlencode(params)}"

    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            # Attendre que les cartes soient rendues
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()
            return Parser.parse_liste_catalogue(html)
    except Exception:
        logger.exception(f"Erreur catalogue liste {url!r}")
        return []


# ---------------------------------------------------------------------------
# Catalogue complet d'un animé (Playwright)
# ---------------------------------------------------------------------------

def _getcatalogue_sync(slug: str) -> Optional[Catalogue]:
    catalogue_url = f"{BASE_SAMA_URL}catalogue/{slug}/"
    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)
            page.goto(catalogue_url, timeout=30000, wait_until="domcontentloaded")

            if "Introuvable" in page.title() or "404" in page.title():
                browser.close()
                return None

            try:
                page.wait_for_selector("#sousBlocMiddle", timeout=10000)
            except Exception:
                browser.close()
                logger.warning(f"#sousBlocMiddle absent : {catalogue_url}")
                return None

            html = page.locator("#sousBlocMiddle").inner_html()
            browser.close()
            return Parser.parse_catalogue(html, slug=slug)
    except Exception:
        logger.exception(f"Erreur catalogue {catalogue_url!r}")
        return None


# ---------------------------------------------------------------------------
# Épisodes d'une saison (Playwright)
# ---------------------------------------------------------------------------

def _get_episodes_sync(url_saison: str) -> dict[int, list[dict]]:
    """
    Retourne { ep_num: [ {lecteur, player_url}, … ], … }
    Retourne {} si la page est introuvable (404) ou bloquée.
    """
    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)
            resp = page.goto(url_saison, timeout=60000)

            # 404 → langue non disponible pour ce contenu
            if resp and resp.status == 404:
                logger.info(f"404 — langue non disponible : {url_saison}")
                browser.close()
                return {}

            try:
                page.wait_for_selector("#selectEpisodes", timeout=15000)
            except Exception:
                _debug_page_state(page, "episodes")
                if _is_blocked(page):
                    logger.error(f"Page bloquée (FortiGuard ?) : {url_saison}")
                browser.close()
                return {}

            options = page.locator("#selectEpisodes option").all_text_contents()
            total   = len(options)
            logger.info(f"{total} épisodes/chapitres sur {url_saison}")

            results: dict[int, list[dict]] = {}
            for idx in range(total):
                # Sélection par index — fonctionne quel que soit le libellé
                # ("Episode 1", "Film 1", "Chapitre 1", …)
                page.select_option("#selectEpisodes", index=idx)
                page.wait_for_timeout(300)

                # Numéro extrait du texte de l'option
                label  = options[idx].strip()
                num_m  = re.search(r"(\d+(?:[.,]\d+)?)", label)
                ep_num = int(float(num_m.group(1).replace(",", "."))) if num_m else idx + 1

                lecteurs = page.locator("#selectLecteurs option").all_text_contents()
                ep_data  = []
                for i, nom in enumerate(lecteurs):
                    page.select_option("#selectLecteurs", index=i)
                    page.wait_for_timeout(200)
                    player_url = page.locator("#playerDF").get_attribute("src")
                    ep_data.append({"lecteur": nom.strip(), "player_url": player_url})

                results[ep_num] = ep_data

            browser.close()
            return results
    except Exception:
        logger.exception(f"Erreur épisodes {url_saison!r}")
        return {}


# ---------------------------------------------------------------------------
# Chapitres d'un scan (Playwright — la page peut être JS-rendue)
# ---------------------------------------------------------------------------

def _get_scan_chapitres_sync(url_scan: str) -> list[dict]:
    """
    Scrape tous les chapitres d'un scan et leurs images.

    Structure réelle anime-sama.to :
      #selectEpisodes   → select des chapitres
      #modeScroll       → bouton pour afficher toutes les images du chapitre d'un coup
      #scansPlacement   → div contenant les <img> du chapitre courant
      #nextChapitre     → bouton chapitre suivant
      #prevChapitre     → bouton chapitre précédent

    Pour chaque chapitre on :
      1. Sélectionne via #selectEpisodes (index)
      2. Active #modeScroll (une seule fois en début de session)
      3. Scrolle jusqu'en bas pour déclencher le lazy-loading
      4. Récupère les src/data-src de tous les img dans #scansPlacement
    """
    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)
            resp = page.goto(url_scan, timeout=30000, wait_until="domcontentloaded")

            if resp and resp.status == 404:
                logger.info(f"404 — langue non disponible : {url_scan}")
                browser.close()
                return []

            # Scans : le sélecteur de chapitres s'appelle #selectChapitres
            try:
                page.wait_for_selector("#selectChapitres", timeout=10000)
            except Exception:
                _debug_page_state(page, "scan-chapitres")
                if _is_blocked(page):
                    logger.error(f"Page bloquée (FortiGuard ?) : {url_scan}")
                browser.close()
                return []

            # Activer le mode scroll une seule fois (sticky pour toute la session)
            try:
                page.wait_for_selector("#modeScroll", timeout=3000)
                page.click("#modeScroll")
                page.wait_for_timeout(600)
            except Exception:
                pass  # déjà en mode scroll ou bouton absent

            options = page.locator("#selectChapitres option").all_text_contents()
            total   = len(options)
            logger.info(f"{total} chapitres sur {url_scan}")

            chapitres = []
            for idx in range(total):
                page.select_option("#selectChapitres", index=idx)
                page.wait_for_timeout(700)  # laisser le JS charger les images

                label = options[idx].strip()
                num_m = re.search(r"(\d+(?:[.,]\d+)?)", label)
                num   = float(num_m.group(1).replace(",", ".")) if num_m else float(idx + 1)

                # Attendre qu'au moins une image apparaisse
                try:
                    page.wait_for_selector("#scansPlacement img", timeout=5000)
                except Exception:
                    if idx == 0:
                        # Premier chapitre : loguer les IDs présents pour debug
                        _debug_page_state(page, f"scan-ch{idx}")
                    logger.warning(f"  #scansPlacement absent pour chapitre {idx}")

                # Scroller jusqu'en bas pour déclencher le lazy-loading
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(500)

                # Récupérer toutes les URLs d'images
                # Priorité : data-src (lazy) > src (chargée)
                images: list[str] = page.evaluate("""
                    () => Array.from(
                        document.querySelectorAll('#scansPlacement img')
                    ).map(img =>
                        img.getAttribute('data-src') ||
                        img.getAttribute('data-lazy-src') ||
                        img.getAttribute('data-original') ||
                        img.src || ''
                    ).filter(u => u && u.startsWith('http'))
                """)

                chapitres.append({
                    "numero":   num,
                    "titre":    label,
                    "url":      page.url,
                    "images":   images,
                    "lecteurs": [],
                })
                logger.info(f"  scan chapitre {num} : {len(images)} image(s)")

            browser.close()
            return chapitres

    except Exception:
        logger.exception(f"Erreur scan chapitres {url_scan!r}")
        return []


# ---------------------------------------------------------------------------
# Planning (/planning/)  —  HTML statique, httpx suffit
# ---------------------------------------------------------------------------

def _get_planning_sync() -> list[dict]:
    try:
        resp = httpx.get(
            f"{BASE_SAMA_URL}planning/",
            headers={"User-Agent": _UA},
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return Parser.parse_planning(resp.text)
    except Exception:
        logger.exception("Erreur récupération planning")
        return []


# ---------------------------------------------------------------------------
# API async publique
# ---------------------------------------------------------------------------

async def search_anime(query: str) -> list[dict]:
    """Recherche via la barre de recherche du site (Playwright)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _search_sync, query)


async def search_catalogue_site(
    q: Optional[str] = None,
    type_contenu: Optional[str] = None,
    lang: Optional[str] = None,
    statut: Optional[str] = None,
    genres: Optional[list[str]] = None,
    page_num: int = 1,
) -> list[dict]:
    """Scrape /catalogue/ avec filtres (Playwright)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        _search_catalogue_site_sync,
        q, type_contenu, lang, statut, genres, page_num,
    )


async def getcatalogue(slug: str) -> Optional[Catalogue]:
    """Récupère la structure d'un catalogue (sans épisodes)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _getcatalogue_sync, slug)


async def get_episodes(url_saison: str) -> dict[int, list[dict]]:
    """Extrait tous les épisodes d'une saison."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_episodes_sync, url_saison)


async def get_scan_chapitres(url_scan: str) -> list[dict]:
    """Extrait la liste des chapitres d'un scan."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_scan_chapitres_sync, url_scan)


async def get_planning() -> list[dict]:
    """Récupère le planning de la semaine (HTTP simple)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_planning_sync)


# ---------------------------------------------------------------------------
# Genres (/catalogue/)  —  Playwright (genres sont JS-rendus)
# ---------------------------------------------------------------------------

def _is_valid_genre(txt: str) -> bool:
    """Genre valide : non vide, contient au moins une lettre, longueur 2–50."""
    cleaned = re.sub(r"[\s ​‌‍﻿]+", " ", txt).strip()
    return bool(cleaned) and 2 <= len(cleaned) <= 50 and any(c.isalpha() for c in cleaned)


def _get_genres_sync() -> list[str]:
    """
    Scrape /catalogue/ pour extraire tous les genres disponibles.
    Utilise Playwright (les genres sont JS-rendus — httpx ne les voit pas).
    3 stratégies combinées :
      1. Sélecteurs natifs Playwright (.genre-pill, select, checkbox)
      2. Évaluation JS (variables globales, data-attributes, liens de filtre)
      3. Parse HTML complet post-rendu (BeautifulSoup)
    """
    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)
            page.goto(f"{BASE_SAMA_URL}catalogue/", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)   # laisser le JS charger les cartes et filtres

            genres: set[str] = set()

            # ── Stratégie 1a : .genre-pill dans les cartes catalogue ──────────
            try:
                for txt in page.locator(".genre-pill").all_text_contents():
                    if _is_valid_genre(txt):
                        genres.add(txt.strip())
            except Exception:
                pass

            # ── Stratégie 1b : select[name*=genre] ───────────────────────────
            try:
                for sel_loc in page.locator("select").all():
                    name = (sel_loc.get_attribute("name") or "").lower()
                    iid  = (sel_loc.get_attribute("id")   or "").lower()
                    if "genre" in name or "genre" in iid:
                        for o in sel_loc.locator("option").all_text_contents():
                            if _is_valid_genre(o):
                                genres.add(o.strip())
            except Exception:
                pass

            # ── Stratégie 2 : évaluation JS ──────────────────────────────────
            try:
                js_result = page.evaluate("""
                    () => {
                        // Variables globales communes
                        const candidates = [
                            window.genres, window.allGenres, window.genreList,
                            window.GENRES, window.catalogue_genres,
                            window.filters && window.filters.genres,
                        ];
                        for (const c of candidates) {
                            if (Array.isArray(c) && c.length > 3) return c;
                        }
                        // data-genres sur un conteneur
                        const el = document.querySelector('[data-genres]');
                        if (el) {
                            try { return JSON.parse(el.dataset.genres); } catch {}
                        }
                        // Liens/boutons filtre genre
                        return Array.from(
                            document.querySelectorAll('a[href*="genre"], [data-genre], .filter-genre')
                        ).map(e => (e.dataset.genre || e.textContent || '').trim())
                         .filter(t => t.length >= 2);
                    }
                """)
                if isinstance(js_result, list):
                    for g in js_result:
                        if _is_valid_genre(str(g)):
                            genres.add(str(g).strip())
            except Exception:
                pass

            # ── Stratégie 3 : parse HTML complet post-rendu ──────────────────
            try:
                html = page.content()
                for g in Parser.parse_genres_from_catalogue(html):
                    if _is_valid_genre(g):
                        genres.add(g)
            except Exception:
                pass

            browser.close()
            result = sorted(genres)
            logger.info(f"Genres : {len(result)} genres trouvés")
            return result

    except Exception:
        logger.exception("Erreur récupération genres")
        return []


async def get_genres_from_site() -> list[str]:
    """Extrait tous les genres disponibles sur anime-sama.to/catalogue/."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_genres_sync)
