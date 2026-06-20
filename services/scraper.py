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
    search:        Optional[str]       = None,
    types:         Optional[list[str]] = None,
    langues:       Optional[list[str]] = None,
    statuts:       Optional[list[str]] = None,
    genres:        Optional[list[str]] = None,
    annee_min:     Optional[int]       = None,
    annee_max:     Optional[int]       = None,
    episodes_min:  Optional[int]       = None,
    episodes_max:  Optional[int]       = None,
    chapitres_min: Optional[int]       = None,
    chapitres_max: Optional[int]       = None,
    page_num:      int                 = 1,
) -> list[dict]:
    """
    Scrape /catalogue/ avec les filtres réels d'anime-sama.to.

    Structure URL validée (le JS de la page en a besoin) :
      type[]=Anime&type[]=Scans   → tableau PHP (seulement si sélectionné)
      langue[]=VOSTFR             → idem
      current[]=En cours          → idem (avec accent)
      genre[]=Démons              → idem (avec accents exacts)
      annee_min=&annee_max=       → TOUJOURS présents, même vides
      episodes_min=&episodes_max= → idem
      chapitres_min=&chapitres_max= → idem
      search=naruto               → TOUJOURS présent (vide si pas de texte)
    """
    params: list[tuple[str, str]] = []

    # Tableaux PHP : seulement si des valeurs sont sélectionnées
    for t in (types   or []): params.append(("type[]",    t))
    for l in (langues or []): params.append(("langue[]",  l))
    for s in (statuts or []): params.append(("current[]", s))
    for g in (genres  or []): params.append(("genre[]",   g))

    # Plages : toujours incluses même vides (le JS du site les attend)
    params.append(("annee_min",     str(annee_min)     if annee_min     else ""))
    params.append(("annee_max",     str(annee_max)     if annee_max     else ""))
    params.append(("episodes_min",  str(episodes_min)  if episodes_min  else ""))
    params.append(("episodes_max",  str(episodes_max)  if episodes_max  else ""))
    params.append(("chapitres_min", str(chapitres_min) if chapitres_min else ""))
    params.append(("chapitres_max", str(chapitres_max) if chapitres_max else ""))

    # search : toujours présent (vide si pas de texte)
    params.append(("search", search or ""))

    if page_num > 1:
        params.append(("page", str(page_num)))

    url = f"{BASE_SAMA_URL}catalogue/?{urlencode(params)}"

    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)
            page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # Attendre que les cartes apparaissent dans le DOM
            try:
                page.wait_for_selector("a[href*='/catalogue/']", timeout=8000)
            except Exception:
                pass  # Pas de cartes (0 résultats) ou timeout

            page.wait_for_timeout(1500)  # Attente supplémentaire pour le rendu complet
            html = page.content()

            # ── Debug : logguer un extrait pour comprendre la structure ──────
            a_links = page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href*="/catalogue/"]'))
                    .slice(0, 5)
                    .map(a => ({href: a.href, text: a.innerText.trim().slice(0,40)}))
            """)
            logger.info(f"Catalogue site debug : {len(a_links)} liens /catalogue/ trouvés : {a_links}")

            browser.close()
            results = Parser.parse_liste_catalogue(html)
            logger.info(f"Catalogue site : {len(results)} résultats parsés pour {url!r}")
            return results
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

# Regex pour identifier le segment de langue en fin d'URL
_LANG_SEGMENT_RE = re.compile(
    r'/(vf\d*|vostfr|vastfr|vo|vqc\d*|van|var|vcn|vkr)(/?)$',
    re.IGNORECASE,
)
# Ordre de priorité : VF d'abord, puis VOSTFR, puis VO
_LANG_TRY_ORDER = ["vf", "vostfr", "vo"]


def _replace_lang(url: str, lang: str) -> str:
    """Remplace le segment de langue dans l'URL par `lang`."""
    m = _LANG_SEGMENT_RE.search(url)
    if m:
        return url[:m.start()] + f'/{lang}/'
    # Pas de langue trouvée dans l'URL : on l'ajoute avant le slash final
    return url.rstrip('/') + f'/{lang}/'


def _page_introuvable(page) -> bool:
    """Retourne True si la page affiche 'Accès Introuvable' (soft 404)."""
    try:
        return "Introuvable" in (page.title() or "")
    except Exception:
        return False


def _get_episodes_sync(url_saison: str) -> dict[int, list[dict]]:
    """
    Retourne { ep_num: [ {lecteur, player_url}, … ], … }

    Essaie les langues dans l'ordre VF → VOSTFR → VO quelle que soit
    la langue indiquée dans l'URL d'origine.
    Détecte les pages invalides via :
      - code HTTP 404
      - <title> contenant "Introuvable" (soft-404 retourné en 200 par le site)
    """
    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)

            # ── Sélection de la meilleure langue disponible ──────────────────
            effective_url: str | None = None
            for lang in _LANG_TRY_ORDER:
                candidate = _replace_lang(url_saison, lang)
                resp = page.goto(candidate, timeout=60000)

                if resp and resp.status == 404:
                    logger.info(f"  [{lang}] 404 HTTP — {candidate}")
                    continue

                if _page_introuvable(page):
                    logger.info(f"  [{lang}] Page 'Introuvable' — {candidate}")
                    continue

                if _is_blocked(page):
                    logger.error(f"Page bloquée (FortiGuard ?) : {candidate}")
                    browser.close()
                    return {}

                try:
                    page.wait_for_selector("#selectEpisodes", timeout=15000)
                    effective_url = candidate
                    logger.info(f"Langue retenue : {lang} → {candidate}")
                    break
                except Exception:
                    _debug_page_state(page, f"no-ep-{lang}")
                    logger.info(f"  [{lang}] #selectEpisodes absent — {candidate}")
                    continue

            if not effective_url:
                browser.close()
                logger.info(f"Aucune langue disponible pour : {url_saison}")
                return {}

            # ── Scraping des épisodes (page déjà chargée et valide) ──────────
            options = page.locator("#selectEpisodes option").all_text_contents()
            total   = len(options)
            logger.info(f"{total} épisodes/chapitres sur {effective_url}")

            results: dict[int, list[dict]] = {}
            for idx in range(total):
                page.select_option("#selectEpisodes", index=idx)
                page.wait_for_timeout(300)

                label  = options[idx].strip()
                num_m  = re.search(r"(\d+(?:[.,]\d+)?)", label)
                ep_num = int(float(num_m.group(1).replace(",", "."))) if num_m else idx + 1

                lecteur_noms = page.locator("#selectLecteurs option").all_text_contents()
                ep_data:   list[dict] = []
                seen_urls: set[str]   = set()
                prev_src = ""

                for i, nom in enumerate(lecteur_noms):
                    page.select_option("#selectLecteurs", index=i)

                    # Attendre que #playerDF.src change réellement (max 2 s)
                    try:
                        page.wait_for_function(
                            """(p) => {
                                const f = document.getElementById('playerDF');
                                const s = f ? (f.getAttribute('src') || f.src || '') : '';
                                return s.length > 4 && s !== p;
                            }""",
                            arg=prev_src,
                            timeout=2000,
                        )
                    except Exception:
                        page.wait_for_timeout(600)

                    player_url = (page.locator("#playerDF").get_attribute("src") or "").strip()

                    if player_url and player_url not in seen_urls:
                        ep_data.append({"lecteur": nom.strip(), "player_url": player_url})
                        seen_urls.add(player_url)
                        prev_src = player_url

                if ep_data:
                    results[ep_num] = ep_data
                    logger.debug(f"  ep {ep_num} : {len(ep_data)} lecteur(s)")

            logger.info(f"{len(results)} épisodes ({effective_url})")
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
    search:        Optional[str]       = None,
    types:         Optional[list[str]] = None,
    langues:       Optional[list[str]] = None,
    statuts:       Optional[list[str]] = None,
    genres:        Optional[list[str]] = None,
    annee_min:     Optional[int]       = None,
    annee_max:     Optional[int]       = None,
    episodes_min:  Optional[int]       = None,
    episodes_max:  Optional[int]       = None,
    chapitres_min: Optional[int]       = None,
    chapitres_max: Optional[int]       = None,
    page_num:      int                 = 1,
) -> list[dict]:
    """Scrape /catalogue/ avec filtres réels anime-sama.to (Playwright)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        _search_catalogue_site_sync,
        search, types, langues, statuts, genres,
        annee_min, annee_max, episodes_min, episodes_max,
        chapitres_min, chapitres_max, page_num,
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

    Structure réelle anime-sama.to (validée 2026-06) :
      <div id="genreList">
        <label class="filter-checkbox-item">
          <input type="checkbox" class="filter-checkbox" name="genre[]" value="Action">
          <span>Action</span>
        </label>
        ...
      </div>

    Stratégies dans l'ordre :
      0. #genreList input.filter-checkbox → attribut value  (sélecteur validé)
      1. Parse HTML complet post-rendu (BeautifulSoup, même sélecteur)
      2. .genre-pill dans les cartes catalogue (fallback ancien comportement)
    """
    try:
        with sync_playwright() as p:
            browser, page = _open_page(p)
            page.goto(f"{BASE_SAMA_URL}catalogue/", timeout=30000, wait_until="domcontentloaded")

            # Attendre que #genreList soit présent (rendu côté serveur, quasi-immédiat)
            try:
                page.wait_for_selector("#genreList input.filter-checkbox", timeout=8000)
            except Exception:
                page.wait_for_timeout(3000)

            genres: set[str] = set()

            # ── Stratégie 0 : #genreList input[name="genre[]"] ── (prioritaire)
            try:
                values = page.evaluate("""
                    () => Array.from(
                        document.querySelectorAll('#genreList input.filter-checkbox')
                    ).map(i => i.value).filter(v => v && v.trim().length >= 2)
                """)
                if isinstance(values, list):
                    for v in values:
                        if _is_valid_genre(str(v)):
                            genres.add(str(v).strip())
                logger.info(f"Genres (stratégie #genreList) : {len(genres)} trouvés")
            except Exception:
                pass

            # ── Stratégie 1 : parse HTML complet (BeautifulSoup) ─────────────
            if len(genres) < 5:
                try:
                    html = page.content()
                    for g in Parser.parse_genres_from_catalogue(html):
                        if _is_valid_genre(g):
                            genres.add(g)
                    logger.info(f"Genres (stratégie HTML) : {len(genres)} après parse")
                except Exception:
                    pass

            # ── Stratégie 2 : .genre-pill des cartes ──────────────────────────
            if len(genres) < 5:
                try:
                    for txt in page.locator(".genre-pill").all_text_contents():
                        if _is_valid_genre(txt):
                            genres.add(txt.strip())
                except Exception:
                    pass

            browser.close()
            result = sorted(genres)
            logger.info(f"Genres : {len(result)} genres trouvés au total")
            return result

    except Exception:
        logger.exception("Erreur récupération genres")
        return []


async def get_genres_from_site() -> list[str]:
    """Extrait tous les genres disponibles sur anime-sama.to/catalogue/."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_genres_sync)
