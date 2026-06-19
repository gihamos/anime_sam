"""
CLI anime-sama — toutes les fonctions de l'API accessibles en ligne de commande.

Utilisation :
  py cli.py rechercher "naruto"
  py cli.py rechercher "naruto" --type anime --lang vostfr --etat en_cours
  py cli.py get dragon-ball
  py cli.py sync-content dragon-ball
  py cli.py saisons naruto
  py cli.py films naruto
  py cli.py scans naruto
  py cli.py episodes naruto saison1 --lang vostfr
  py cli.py chapitres naruto 0
  py cli.py rafraichir dragon-ball
  py cli.py planning
  py cli.py liste
  py cli.py update-all
"""

import asyncio
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

app     = typer.Typer(help="CLI Anime Sama — accès au catalogue anime-sama.to")
console = Console()


def _run(coro):
    return asyncio.run(coro)


def _get_or_fetch(slug: str) -> dict | None:
    """Retourne le catalogue depuis la DB. Le scrape et le sauvegarde s'il est absent."""
    from services.catalogue_service import get_catalogue
    return _run(get_catalogue(slug))


# ---------------------------------------------------------------------------
# rechercher
# ---------------------------------------------------------------------------
@app.command()
def rechercher(
    query: str                  = typer.Argument(..., help="Titre à rechercher"),
    type:  Optional[str]        = typer.Option(None, "--type",  help="anime|scan|film|autre"),
    lang:  Optional[str]        = typer.Option(None, "--lang",  help="vostfr|vf|vo…"),
    etat:  Optional[str]        = typer.Option(None, "--etat",  help="en_cours|termine|abandonne"),
    genre: Optional[str]        = typer.Option(None, "--genre", help="Genres séparés par virgule"),
    page:  int                  = typer.Option(1,    "--page"),
    site:  bool                 = typer.Option(False,"--site",  help="Forcer la recherche sur le site"),
):
    """Recherche un animé en DB (avec filtres). Fallback sur le site si absent."""
    from services.catalogue_service import rechercher as svc_rechercher, rechercher_sur_site

    genres_list = [g.strip() for g in genre.split(",")] if genre else None

    with console.status(f"Recherche de [bold]{query}[/bold]..."):
        if site:
            results = _run(rechercher_sur_site(
                q=query, type_contenu=type, lang=lang, statut=etat,
                genres=genres_list, page=page
            ))
        else:
            results = _run(svc_rechercher(
                q=query, type_contenu=type, lang=lang, etat=etat,
                genres=genres_list, page=page
            ))

    if not results:
        rprint("[red]Aucun résultat.[/red]")
        raise typer.Exit(1)

    table = Table(title=f"{len(results)} résultat(s) pour « {query} »")
    table.add_column("Titre",  style="cyan")
    table.add_column("Slug")
    table.add_column("Type")
    table.add_column("État")
    table.add_column("Langues")

    for r in results:
        table.add_row(
            r.get("nom") or r.get("title") or "?",
            r.get("slug", "?"),
            r.get("type_contenu", "?"),
            r.get("etat", "?"),
            ", ".join(r.get("langues", [])),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------
@app.command()
def get(slug: str = typer.Argument(..., help="Slug de l'animé (ex: dragon-ball)")):
    """Récupère le catalogue complet (DB ou scraping si absent)."""
    with console.status(f"Chargement de [bold]{slug}[/bold]..."):
        cat = _get_or_fetch(slug)

    if not cat:
        rprint(f"[red]Catalogue '{slug}' introuvable.[/red]")
        raise typer.Exit(1)

    rprint(f"\n[bold cyan]{cat.get('nom')}[/bold cyan]  "
           f"[dim]({cat.get('etat')} · {cat.get('type_contenu')})[/dim]")
    if cat.get("titre_alternatif"):
        rprint(f"[dim]{cat['titre_alternatif']}[/dim]")
    if cat.get("genres"):
        rprint("Genres  : " + ", ".join(cat["genres"]))
    if cat.get("langues"):
        rprint("Langues : " + ", ".join(cat["langues"]))
    syn = cat.get("synopsis") or ""
    if syn:
        rprint(f"\n{syn[:400]}{'…' if len(syn) > 400 else ''}")

    saison_list = cat.get("saisons", [])
    film_list   = cat.get("films",   [])
    scan_list   = cat.get("scans",   [])

    if saison_list:
        t = Table(title="Saisons", show_lines=False)
        t.add_column("Nom",      style="green")
        t.add_column("Lang")
        t.add_column("Épisodes", justify="right")
        t.add_column("Synced",   justify="center")
        for s in saison_list:
            ep_count = len(s.get("episodes", []))
            total    = s.get("total_episodes") or ep_count
            t.add_row(s["nom"], s.get("lang","?"), str(total), "✓" if ep_count else "–")
        console.print(t)

    if film_list:
        t = Table(title="Films", show_lines=False)
        t.add_column("Nom",      style="yellow")
        t.add_column("Lang")
        t.add_column("Lecteurs", justify="right")
        t.add_column("Synced",   justify="center")
        for f in film_list:
            lect = len(f.get("videos", []))
            t.add_row(f["nom"], f.get("lang","?"), str(lect), "✓" if lect else "–")
        console.print(t)

    if scan_list:
        t = Table(title="Scans / Mangas", show_lines=False)
        t.add_column("Nom",       style="magenta")
        t.add_column("Lang")
        t.add_column("Chapitres", justify="right")
        t.add_column("Synced",    justify="center")
        for s in scan_list:
            chaps = len(s.get("chapitres", []))
            t.add_row(s["nom"], s.get("lang") or "?", str(chaps), "✓" if chaps else "–")
        console.print(t)

    synced = cat.get("episodes_synced", False)
    hint   = f"py cli.py sync-content {slug}"
    rprint(f"\n[{'green' if synced else 'yellow'}]"
           f"Contenu {'synchronisé ✓' if synced else f'non synchronisé — lancez : {hint}'}[/]")


# ---------------------------------------------------------------------------
# sync-content
# ---------------------------------------------------------------------------
@app.command(name="sync-content")
def sync_content(slug: str = typer.Argument(..., help="Slug de l'animé")):
    """Synchronise tout le contenu : saisons, films et scans/mangas."""
    from services.catalogue_service import sync_content_bg

    rprint(f"[yellow]Synchronisation du contenu de [bold]{slug}[/bold]...[/yellow]")
    rprint("[dim]Cela peut prendre plusieurs minutes.[/dim]")

    count = _run(sync_content_bg(slug))
    rprint(f"[green]✓ {count} élément(s) chargé(s) (épisodes + chapitres).[/green]")


# ---------------------------------------------------------------------------
# saisons — liste les saisons d'un catalogue
# ---------------------------------------------------------------------------
@app.command()
def saisons(
    slug: str           = typer.Argument(..., help="Slug de l'animé"),
    lang: Optional[str] = typer.Option(None, "--lang", help="Filtre langue : vf|vostfr|vo"),
):
    """Liste les saisons disponibles (DB ou scraping si absent)."""
    with console.status(f"Chargement de [bold]{slug}[/bold]..."):
        cat = _get_or_fetch(slug)

    if not cat:
        rprint(f"[red]Catalogue '{slug}' introuvable.[/red]")
        raise typer.Exit(1)

    items = cat.get("saisons", [])
    if lang:
        items = [s for s in items if s.get("lang", "").lower() == lang.lower()]

    if not items:
        rprint("[yellow]Aucune saison trouvée.[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Saisons — {cat.get('nom')}")
    table.add_column("#",      justify="right", style="dim")
    table.add_column("Nom",    style="green")
    table.add_column("Lang")
    table.add_column("Slug")
    table.add_column("Épisodes", justify="right")
    table.add_column("Synced",   justify="center")

    for idx, s in enumerate(items):
        ep_count = len(s.get("episodes", []))
        total    = s.get("total_episodes") or ep_count
        synced   = "✓" if ep_count > 0 else "–"
        table.add_row(str(idx), s.get("nom","?"), s.get("lang","?"),
                      s.get("slug","?"), str(total), synced)
    console.print(table)
    rprint(f"\n[dim]py cli.py episodes {slug} <slug-saison> --lang <lang>[/dim]")


# ---------------------------------------------------------------------------
# films — liste les films d'un catalogue
# ---------------------------------------------------------------------------
@app.command()
def films(
    slug: str           = typer.Argument(..., help="Slug de l'animé"),
    lang: Optional[str] = typer.Option(None, "--lang", help="Filtre langue : vf|vostfr|vo"),
):
    """Liste les films disponibles (DB ou scraping si absent)."""
    with console.status(f"Chargement de [bold]{slug}[/bold]..."):
        cat = _get_or_fetch(slug)

    if not cat:
        rprint(f"[red]Catalogue '{slug}' introuvable.[/red]")
        raise typer.Exit(1)

    items = cat.get("films", [])
    if lang:
        items = [f for f in items if f.get("lang", "").lower() == lang.lower()]

    if not items:
        rprint("[yellow]Aucun film trouvé.[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Films — {cat.get('nom')}")
    table.add_column("#",    justify="right", style="dim")
    table.add_column("Nom",  style="yellow")
    table.add_column("Lang")
    table.add_column("Slug")
    table.add_column("Lecteurs", justify="right")
    table.add_column("Synced",   justify="center")

    for idx, f in enumerate(items):
        lect_count = len(f.get("videos", []))
        table.add_row(str(idx), f.get("nom","?"), f.get("lang","?"),
                      f.get("slug","?"), str(lect_count), "✓" if lect_count > 0 else "–")
    console.print(table)


# ---------------------------------------------------------------------------
# scans — liste les scans/mangas d'un catalogue
# ---------------------------------------------------------------------------
@app.command()
def scans(
    slug: str           = typer.Argument(..., help="Slug de l'animé"),
    lang: Optional[str] = typer.Option(None, "--lang", help="Filtre langue : vf|vostfr|vo"),
):
    """Liste les scans/mangas disponibles (DB ou scraping si absent)."""
    with console.status(f"Chargement de [bold]{slug}[/bold]..."):
        cat = _get_or_fetch(slug)

    if not cat:
        rprint(f"[red]Catalogue '{slug}' introuvable.[/red]")
        raise typer.Exit(1)

    items = cat.get("scans", [])
    if lang:
        items = [s for s in items if s.get("lang", "").lower() == lang.lower()]

    if not items:
        rprint("[yellow]Aucun scan trouvé.[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Scans — {cat.get('nom')}")
    table.add_column("#",          justify="right", style="dim")
    table.add_column("Nom",        style="magenta")
    table.add_column("Lang")
    table.add_column("Chapitres",  justify="right")
    table.add_column("Images",     justify="right")
    table.add_column("Synced",     justify="center")

    for idx, s in enumerate(items):
        chaps      = s.get("chapitres", [])
        nb_images  = sum(len(c.get("images", [])) for c in chaps)
        table.add_row(str(idx), s.get("nom","?"), s.get("lang") or "?",
                      str(len(chaps)), str(nb_images), "✓" if chaps else "–")
    console.print(table)
    rprint(f"\n[dim]py cli.py chapitres {slug} <index-scan>[/dim]")


# ---------------------------------------------------------------------------
# episodes — épisodes d'une saison depuis la DB
# ---------------------------------------------------------------------------
@app.command()
def episodes(
    slug:   str           = typer.Argument(..., help="Slug de l'animé"),
    saison: str           = typer.Argument(..., help="Slug de la saison (ex: saison1)"),
    lang:   str           = typer.Option("vf", "--lang", help="Langue prioritaire : vf|vostfr|vo"),
    tout:   bool          = typer.Option(False, "--tout", help="Afficher tous les lecteurs"),
):
    """
    Affiche les épisodes d'une saison depuis la DB.

    Le catalogue est récupéré en DB (scraping + sauvegarde si absent).
    Si les épisodes ne sont pas encore synchronisés, un message guide vers sync-content.
    """
    with console.status(f"Chargement de [bold]{slug}[/bold]..."):
        cat = _get_or_fetch(slug)

    if not cat:
        rprint(f"[red]Catalogue '{slug}' introuvable.[/red]")
        raise typer.Exit(1)

    all_saisons = cat.get("saisons", [])

    # Chercher la saison par slug + langue, avec fallback sur les autres langues
    lang_priority = [lang] + [l for l in ("vf", "vostfr", "vo") if l != lang]
    found = None
    for pref_lang in lang_priority:
        for s in all_saisons:
            if s.get("slug", "").lower() == saison.lower() \
               and s.get("lang", "").lower() == pref_lang.lower():
                found = s
                break
        if found:
            break

    # Fallback : slug uniquement (ignore la langue)
    if not found:
        for s in all_saisons:
            if s.get("slug", "").lower() == saison.lower():
                found = s
                break

    if not found:
        rprint(f"[red]Saison '{saison}' introuvable pour '{slug}'.[/red]")
        rprint(f"[dim]Slugs disponibles : {[s.get('slug') for s in all_saisons]}[/dim]")
        raise typer.Exit(1)

    eps = found.get("episodes", [])
    if not eps:
        rprint(f"[yellow]Épisodes non encore synchronisés pour "
               f"[bold]{found.get('nom')}[/bold].[/yellow]")
        rprint(f"[dim]Lancez d'abord : py cli.py sync-content {slug}[/dim]")
        raise typer.Exit(0)

    table = Table(title=f"{found.get('nom')} ({found.get('lang','?').upper()})"
                        f" — {len(eps)} épisode(s)")
    table.add_column("Ep",      justify="right", style="bold")
    table.add_column("Titre",   style="cyan")
    if tout:
        table.add_column("Lecteurs")
    else:
        table.add_column("Lecteur principal")

    for ep in sorted(eps, key=lambda e: e.get("numero", 0)):
        videos = ep.get("videos", [])
        if tout:
            lect_str = "\n".join(
                f"[dim]{v.get('lecteur')}[/dim] {v.get('player_url') or ''}"
                for v in videos
            )
        else:
            v = videos[0] if videos else {}
            lect_str = f"[dim]{v.get('lecteur','')}[/dim]  {v.get('player_url') or '–'}"

        table.add_row(
            str(ep.get("numero", "?")),
            ep.get("titre") or "",
            lect_str,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# chapitres — chapitres d'un scan depuis la DB
# ---------------------------------------------------------------------------
@app.command()
def chapitres(
    slug:       str = typer.Argument(..., help="Slug de l'animé"),
    scan_index: int = typer.Argument(0,   help="Index du scan (voir : py cli.py scans <slug>)"),
    images:     bool = typer.Option(False, "--images", help="Afficher les URLs des images"),
):
    """
    Affiche les chapitres d'un scan depuis la DB.

    Le catalogue est récupéré en DB (scraping + sauvegarde si absent).
    Si les chapitres ne sont pas encore synchronisés, un message guide vers sync-content.
    """
    with console.status(f"Chargement de [bold]{slug}[/bold]..."):
        cat = _get_or_fetch(slug)

    if not cat:
        rprint(f"[red]Catalogue '{slug}' introuvable.[/red]")
        raise typer.Exit(1)

    scan_list = cat.get("scans", [])
    if scan_index >= len(scan_list):
        rprint(f"[red]Index {scan_index} invalide — {len(scan_list)} scan(s) disponible(s).[/red]")
        raise typer.Exit(1)

    scan = scan_list[scan_index]
    chaps = scan.get("chapitres", [])

    if not chaps:
        rprint(f"[yellow]Chapitres non encore synchronisés pour "
               f"[bold]{scan.get('nom')}[/bold].[/yellow]")
        rprint(f"[dim]Lancez d'abord : py cli.py sync-content {slug}[/dim]")
        raise typer.Exit(0)

    table = Table(title=f"{scan.get('nom')} — {len(chaps)} chapitre(s)")
    table.add_column("Ch.",    justify="right", style="bold")
    table.add_column("Titre",  style="cyan")
    table.add_column("Images", justify="right")
    if images:
        table.add_column("URL première image")

    for ch in sorted(chaps, key=lambda c: c.get("numero", 0)):
        imgs = ch.get("images", [])
        row  = [str(ch.get("numero","?")), ch.get("titre") or "", str(len(imgs))]
        if images:
            row.append(imgs[0] if imgs else "–")
        table.add_row(*row)
    console.print(table)


# ---------------------------------------------------------------------------
# rafraichir
# ---------------------------------------------------------------------------
@app.command()
def rafraichir(slug: str = typer.Argument(..., help="Slug de l'animé")):
    """Force le re-scraping de la structure d'un catalogue."""
    from services.catalogue_service import rafraichir_catalogue

    with console.status(f"Rafraîchissement de [bold]{slug}[/bold]..."):
        cat = _run(rafraichir_catalogue(slug))

    if not cat:
        rprint(f"[red]Impossible de rafraîchir '{slug}'.[/red]")
        raise typer.Exit(1)
    rprint(f"[green]✓ '{cat.get('nom')}' mis à jour.[/green]")


# ---------------------------------------------------------------------------
# planning
# ---------------------------------------------------------------------------
@app.command()
def planning():
    """Affiche le planning de la semaine en cours."""
    from services.scraper import get_planning

    with console.status("Récupération du planning..."):
        data = _run(get_planning())

    if not data:
        rprint("[red]Planning indisponible.[/red]")
        raise typer.Exit(1)

    for jour_data in data:
        rprint(f"\n[bold cyan]{jour_data['jour']}[/bold cyan]"
               f"  [dim]{jour_data.get('date') or ''}[/dim]")
        animes = jour_data.get("animes", [])
        if not animes:
            rprint("  [dim]Aucun animé[/dim]")
            continue
        for a in animes:
            heure = f"[dim]{a.get('heure') or '??h??'}[/dim]  "
            rprint(f"  {heure}[green]{a['titre']}[/green]  "
                   f"[yellow]{a.get('saison_info') or ''}[/yellow]  "
                   f"[dim]{a.get('lang', '')}[/dim]")


# ---------------------------------------------------------------------------
# liste
# ---------------------------------------------------------------------------
@app.command()
def liste():
    """Liste tous les catalogues en DB."""
    import db.repository as repo

    with console.status("Chargement..."):
        items = _run(repo.get_all_summary())

    if not items:
        rprint("[yellow]Aucun catalogue en base.[/yellow]")
        return

    table = Table(title=f"{len(items)} catalogue(s) en base")
    table.add_column("Nom",    style="cyan")
    table.add_column("Slug")
    table.add_column("Type")
    table.add_column("État")
    table.add_column("Synced", justify="center")
    table.add_column("MAJ")

    for item in items:
        table.add_row(
            item.get("nom", "?"),
            item.get("slug", "?"),
            item.get("type_contenu", "?"),
            item.get("etat", "?"),
            "✓" if item.get("episodes_synced") else "–",
            (item.get("updated_at") or "")[:10],
        )
    console.print(table)


# ---------------------------------------------------------------------------
# update-all
# ---------------------------------------------------------------------------
@app.command(name="update-all")
def update_all():
    """Met à jour la structure de tous les catalogues EN_COURS en DB."""
    from services.catalogue_service import mettre_a_jour_tous

    with console.status("Mise à jour de tous les catalogues..."):
        count = _run(mettre_a_jour_tous())
    rprint(f"[green]✓ {count} catalogue(s) mis à jour.[/green]")


if __name__ == "__main__":
    app()
