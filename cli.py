"""
CLI anime-sama — toutes les fonctions de l'API accessibles en ligne de commande.

Utilisation :
  py cli.py rechercher "naruto"
  py cli.py rechercher "naruto" --type anime --lang vostfr --etat en_cours
  py cli.py get dragon-ball
  py cli.py sync-content dragon-ball
  py cli.py episodes naruto saison1 --lang vostfr
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
    """Récupère le catalogue complet (DB ou scraping)."""
    from services.catalogue_service import get_catalogue

    with console.status(f"Chargement de [bold]{slug}[/bold]..."):
        cat = _run(get_catalogue(slug))

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

    saisons = cat.get("saisons", [])
    films   = cat.get("films",   [])
    scans   = cat.get("scans",   [])

    if saisons:
        t = Table(title="Saisons", show_lines=False)
        t.add_column("Nom",  style="green")
        t.add_column("Lang")
        t.add_column("Épisodes", justify="right")
        for s in saisons:
            t.add_row(s["nom"], s["lang"], str(s.get("total_episodes") or len(s.get("episodes", []))))
        console.print(t)

    if films:
        t = Table(title="Films", show_lines=False)
        t.add_column("Nom", style="yellow")
        t.add_column("Lang")
        for f in films:
            t.add_row(f["nom"], f["lang"])
        console.print(t)

    if scans:
        t = Table(title="Scans", show_lines=False)
        t.add_column("Nom", style="magenta")
        for s in scans:
            t.add_row(s["nom"])
        console.print(t)

    synced = cat.get("episodes_synced", False)
    rprint(f"\n[{'green' if synced else 'yellow'}]"
           f"Épisodes {'synchronisés ✓' if synced else 'non synchronisés — lancez : py cli.py sync-content ' + slug}[/]")


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
# episodes (on-demand pour une saison)
# ---------------------------------------------------------------------------
@app.command()
def episodes(
    slug:   str           = typer.Argument(..., help="Slug de l'animé"),
    saison: str           = typer.Argument(..., help="Ex: saison1"),
    lang:   str           = typer.Option("vostfr", help="Code langue"),
):
    """Affiche les épisodes d'une saison (scraping direct, sans passer par la DB)."""
    from services.scraper import get_episodes
    from params import BASE_SAMA_URL

    url = f"{BASE_SAMA_URL}catalogue/{slug}/{saison}/{lang}/"
    with console.status(f"Extraction des épisodes de [bold]{slug}/{saison}/{lang}[/bold]..."):
        data = _run(get_episodes(url))

    if not data:
        rprint("[red]Aucun épisode trouvé.[/red]")
        raise typer.Exit(1)

    for ep_num, lecteurs in data.items():
        rprint(f"\n[bold]Épisode {ep_num}[/bold]")
        for l in lecteurs:
            rprint(f"  [{l['lecteur']}] {l['player_url']}")


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
