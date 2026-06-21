"""
CLI anime-sama — toutes les fonctions accessibles en ligne de commande.

Catalogue (niveau racine) :
  py cli.py rechercher "naruto"
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

Utilisateurs :
  py cli.py user liste
  py cli.py user get <username>
  py cli.py user creer <username> <password> [--role admin] [--email x]
  py cli.py user supprimer <username>
  py cli.py user bloquer <username> [--raison x] [--jusqu-au DATE]
  py cli.py user debloquer <username>
  py cli.py user perms <username> [--sync] [--no-sync] [--delete] [--no-delete]
  py cli.py user quota <username> --max N --periode day/month/year
  py cli.py user quota <username> --desactiver
  py cli.py user groupes <username>

Groupes :
  py cli.py group liste
  py cli.py group get <id>
  py cli.py group creer <nom> --type catalogue/genre/permission [--desc x]
  py cli.py group supprimer <id>
  py cli.py group membres <id>

Applications API :
  py cli.py app liste
  py cli.py app get <client-id>
  py cli.py app creer <nom> [--desc x]
  py cli.py app supprimer <client-id>
  py cli.py app activer <client-id>
  py cli.py app desactiver <client-id>
  py cli.py app regenerer-secret <client-id>

Sécurité :
  py cli.py security statut
  py cli.py security verrouiller [--raison x]
  py cli.py security deverrouiller
  py cli.py security bans
  py cli.py security bannir <ip> [--raison x]
  py cli.py security debannir <ip>

Téléchargements :
  py cli.py dl historique [--limit 50]
  py cli.py dl quotas
  py cli.py dl quota-set <username> --max-fichiers N --max-go N
  py cli.py dl quota-supprimer <username>
"""

import asyncio
import secrets as _secrets
from datetime import datetime, timezone
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# ── App racine ─────────────────────────────────────────────────────────────────
app     = typer.Typer(help="CLI Anime Sama — catalogue, admin, sécurité, téléchargements")
console = Console()

# ── Sub-apps ──────────────────────────────────────────────────────────────────
user_app     = typer.Typer(help="Gestion des utilisateurs")
group_app    = typer.Typer(help="Gestion des groupes")
app_app      = typer.Typer(help="Gestion des applications API")
security_app = typer.Typer(help="Sécurité : verrous API et bans IP")
dl_app       = typer.Typer(help="Téléchargements : historique et quotas")

app.add_typer(user_app,     name="user",     no_args_is_help=True)
app.add_typer(group_app,    name="group",    no_args_is_help=True)
app.add_typer(app_app,      name="app",      no_args_is_help=True)
app.add_typer(security_app, name="security", no_args_is_help=True)
app.add_typer(dl_app,       name="dl",       no_args_is_help=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _get_or_fetch(slug: str) -> dict | None:
    from services.catalogue_service import get_catalogue
    return _run(get_catalogue(slug))


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "–"
    return iso[:16].replace("T", " ")


# ══════════════════════════════════════════════════════════════════════════════
#  CATALOGUE — commandes racine
# ══════════════════════════════════════════════════════════════════════════════

@app.command()
def rechercher(
    query: str           = typer.Argument(..., help="Titre à rechercher"),
    type:  Optional[str] = typer.Option(None, "--type",  help="anime|scan|film|autre"),
    lang:  Optional[str] = typer.Option(None, "--lang",  help="vostfr|vf|vo…"),
    etat:  Optional[str] = typer.Option(None, "--etat",  help="en_cours|termine|abandonne"),
    genre: Optional[str] = typer.Option(None, "--genre", help="Genres séparés par virgule"),
    page:  int           = typer.Option(1,    "--page"),
    site:  bool          = typer.Option(False,"--site",  help="Forcer la recherche sur le site"),
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
    for s in cat.get("saisons", []):
        rprint(f"  [green]{s['nom']}[/green]  {s.get('lang','')}  {len(s.get('episodes',[]))} ep")
    for f in cat.get("films", []):
        rprint(f"  [yellow]{f['nom']}[/yellow]  {f.get('lang','')}")
    for sc in cat.get("scans", []):
        rprint(f"  [magenta]{sc['nom']}[/magenta]  {sc.get('lang') or ''}  {len(sc.get('chapitres',[]))} ch.")
    synced = cat.get("episodes_synced", False)
    rprint(f"\n[{'green' if synced else 'yellow'}]"
           f"Contenu {'synchronisé ✓' if synced else f'non synchronisé — py cli.py sync-content {slug}'}[/]")


@app.command(name="sync-content")
def sync_content(slug: str = typer.Argument(..., help="Slug de l'animé")):
    """Synchronise tout le contenu : saisons, films et scans/mangas."""
    from services.catalogue_service import sync_content_bg
    rprint(f"[yellow]Synchronisation de [bold]{slug}[/bold]…[/yellow]")
    count = _run(sync_content_bg(slug))
    rprint(f"[green]✓ {count} élément(s) chargé(s).[/green]")


@app.command()
def saisons(
    slug: str           = typer.Argument(...),
    lang: Optional[str] = typer.Option(None, "--lang"),
):
    """Liste les saisons disponibles."""
    cat = _get_or_fetch(slug)
    if not cat:
        rprint(f"[red]'{slug}' introuvable.[/red]"); raise typer.Exit(1)
    items = cat.get("saisons", [])
    if lang:
        items = [s for s in items if s.get("lang","").lower() == lang.lower()]
    table = Table(title=f"Saisons — {cat.get('nom')}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Nom", style="green")
    table.add_column("Lang")
    table.add_column("Slug")
    table.add_column("Épisodes", justify="right")
    for i, s in enumerate(items):
        ep = len(s.get("episodes", []))
        table.add_row(str(i), s.get("nom","?"), s.get("lang","?"),
                      s.get("slug","?"), str(s.get("total_episodes") or ep))
    console.print(table)


@app.command()
def films(
    slug: str           = typer.Argument(...),
    lang: Optional[str] = typer.Option(None, "--lang"),
):
    """Liste les films disponibles."""
    cat = _get_or_fetch(slug)
    if not cat:
        rprint(f"[red]'{slug}' introuvable.[/red]"); raise typer.Exit(1)
    items = cat.get("films", [])
    if lang:
        items = [f for f in items if f.get("lang","").lower() == lang.lower()]
    table = Table(title=f"Films — {cat.get('nom')}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Nom", style="yellow")
    table.add_column("Lang")
    table.add_column("Lecteurs", justify="right")
    for i, f in enumerate(items):
        table.add_row(str(i), f.get("nom","?"), f.get("lang","?"),
                      str(len(f.get("videos",[]))))
    console.print(table)


@app.command()
def scans(
    slug: str           = typer.Argument(...),
    lang: Optional[str] = typer.Option(None, "--lang"),
):
    """Liste les scans/mangas disponibles."""
    cat = _get_or_fetch(slug)
    if not cat:
        rprint(f"[red]'{slug}' introuvable.[/red]"); raise typer.Exit(1)
    items = cat.get("scans", [])
    if lang:
        items = [s for s in items if s.get("lang","").lower() == lang.lower()]
    table = Table(title=f"Scans — {cat.get('nom')}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Nom", style="magenta")
    table.add_column("Lang")
    table.add_column("Chapitres", justify="right")
    for i, s in enumerate(items):
        table.add_row(str(i), s.get("nom","?"), s.get("lang") or "?",
                      str(len(s.get("chapitres",[]))))
    console.print(table)


@app.command()
def episodes(
    slug:   str           = typer.Argument(...),
    saison: str           = typer.Argument(...),
    lang:   str           = typer.Option("vf", "--lang"),
    tout:   bool          = typer.Option(False, "--tout"),
):
    """Affiche les épisodes d'une saison."""
    cat = _get_or_fetch(slug)
    if not cat:
        rprint(f"[red]'{slug}' introuvable.[/red]"); raise typer.Exit(1)
    all_s = cat.get("saisons", [])
    lang_priority = [lang] + [l for l in ("vf", "vostfr", "vo") if l != lang]
    found = None
    for lp in lang_priority:
        for s in all_s:
            if s.get("slug","").lower() == saison.lower() and s.get("lang","").lower() == lp.lower():
                found = s; break
        if found: break
    if not found:
        for s in all_s:
            if s.get("slug","").lower() == saison.lower():
                found = s; break
    if not found:
        rprint(f"[red]Saison '{saison}' introuvable.[/red]"); raise typer.Exit(1)
    eps = found.get("episodes", [])
    if not eps:
        rprint(f"[yellow]Non synchronisé — py cli.py sync-content {slug}[/yellow]")
        raise typer.Exit(0)
    table = Table(title=f"{found.get('nom')} ({found.get('lang','?').upper()}) — {len(eps)} ep")
    table.add_column("Ep", justify="right", style="bold")
    table.add_column("Titre", style="cyan")
    table.add_column("Lecteur(s)" if tout else "Lecteur principal")
    for ep in sorted(eps, key=lambda e: e.get("numero",0)):
        videos = ep.get("videos",[])
        if tout:
            lect = "\n".join(f"{v.get('lecteur','')} {v.get('player_url') or ''}" for v in videos)
        else:
            v = videos[0] if videos else {}
            lect = f"[dim]{v.get('lecteur','')}[/dim]  {v.get('player_url') or '–'}"
        table.add_row(str(ep.get("numero","?")), ep.get("titre") or "", lect)
    console.print(table)


@app.command()
def chapitres(
    slug:       str  = typer.Argument(...),
    scan_index: int  = typer.Argument(0),
    images:     bool = typer.Option(False, "--images"),
):
    """Affiche les chapitres d'un scan."""
    cat = _get_or_fetch(slug)
    if not cat:
        rprint(f"[red]'{slug}' introuvable.[/red]"); raise typer.Exit(1)
    scan_list = cat.get("scans",[])
    if scan_index >= len(scan_list):
        rprint(f"[red]Index {scan_index} invalide.[/red]"); raise typer.Exit(1)
    scan  = scan_list[scan_index]
    chaps = scan.get("chapitres",[])
    if not chaps:
        rprint(f"[yellow]Non synchronisé — py cli.py sync-content {slug}[/yellow]")
        raise typer.Exit(0)
    table = Table(title=f"{scan.get('nom')} — {len(chaps)} chapitre(s)")
    table.add_column("Ch.", justify="right", style="bold")
    table.add_column("Titre", style="cyan")
    table.add_column("Images", justify="right")
    if images:
        table.add_column("1ère image")
    for ch in sorted(chaps, key=lambda c: c.get("numero",0)):
        imgs = ch.get("images",[])
        row  = [str(ch.get("numero","?")), ch.get("titre") or "", str(len(imgs))]
        if images:
            row.append(imgs[0] if imgs else "–")
        table.add_row(*row)
    console.print(table)


@app.command()
def rafraichir(slug: str = typer.Argument(...)):
    """Force le re-scraping de la structure d'un catalogue."""
    from services.catalogue_service import rafraichir_catalogue
    with console.status(f"Rafraîchissement de [bold]{slug}[/bold]..."):
        cat = _run(rafraichir_catalogue(slug))
    if not cat:
        rprint(f"[red]Impossible de rafraîchir '{slug}'.[/red]"); raise typer.Exit(1)
    rprint(f"[green]✓ '{cat.get('nom')}' mis à jour.[/green]")


@app.command()
def planning():
    """Affiche le planning de la semaine."""
    from services.scraper import get_planning
    with console.status("Récupération du planning..."):
        data = _run(get_planning())
    if not data:
        rprint("[red]Planning indisponible.[/red]"); raise typer.Exit(1)
    for jour_data in data:
        rprint(f"\n[bold cyan]{jour_data['jour']}[/bold cyan]  [dim]{jour_data.get('date') or ''}[/dim]")
        for a in jour_data.get("animes",[]):
            rprint(f"  [dim]{a.get('heure') or '??h??'}[/dim]  [green]{a['titre']}[/green]  "
                   f"[yellow]{a.get('saison_info') or ''}[/yellow]  [dim]{a.get('lang','')}[/dim]")


@app.command()
def liste():
    """Liste tous les catalogues en DB."""
    import db.repository as repo
    with console.status("Chargement..."):
        items = _run(repo.get_all_summary())
    if not items:
        rprint("[yellow]Aucun catalogue en base.[/yellow]"); return
    table = Table(title=f"{len(items)} catalogue(s)")
    table.add_column("Nom",    style="cyan")
    table.add_column("Slug")
    table.add_column("Type")
    table.add_column("État")
    table.add_column("Synced", justify="center")
    table.add_column("MAJ")
    for item in items:
        table.add_row(
            item.get("nom","?"), item.get("slug","?"),
            item.get("type_contenu","?"), item.get("etat","?"),
            "✓" if item.get("episodes_synced") else "–",
            (item.get("updated_at") or "")[:10],
        )
    console.print(table)


@app.command(name="update-all")
def update_all():
    """Met à jour la structure de tous les catalogues EN_COURS."""
    from services.catalogue_service import mettre_a_jour_tous
    with console.status("Mise à jour…"):
        count = _run(mettre_a_jour_tous())
    rprint(f"[green]✓ {count} catalogue(s) mis à jour.[/green]")


# ══════════════════════════════════════════════════════════════════════════════
#  UTILISATEURS
# ══════════════════════════════════════════════════════════════════════════════

@user_app.command(name="liste")
def user_liste():
    """Liste tous les utilisateurs."""
    import db.user_repository as user_repo
    users = _run(user_repo.list_users())
    if not users:
        rprint("[yellow]Aucun utilisateur.[/yellow]"); return
    table = Table(title=f"{len(users)} utilisateur(s)")
    table.add_column("Username", style="cyan")
    table.add_column("Email")
    table.add_column("Rôle")
    table.add_column("Actif", justify="center")
    table.add_column("Bloqué", justify="center")
    table.add_column("Groupes", justify="right")
    for u in users:
        table.add_row(
            u.get("username","?"), u.get("email") or "–",
            u.get("role","?"),
            "✓" if u.get("is_active") else "✗",
            "[red]oui[/red]" if u.get("is_blocked") else "–",
            str(len(u.get("groups",[]))),
        )
    console.print(table)


@user_app.command(name="get")
def user_get(username: str = typer.Argument(...)):
    """Affiche le détail d'un utilisateur."""
    import db.user_repository as user_repo
    u = _run(user_repo.find_by_username(username))
    if not u:
        rprint(f"[red]Utilisateur '{username}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"\n[bold cyan]{u.get('username')}[/bold cyan]  [dim]{u.get('role')}[/dim]")
    rprint(f"  Email   : {u.get('email') or '–'}")
    rprint(f"  Actif   : {'oui' if u.get('is_active') else 'non'}")
    rprint(f"  Bloqué  : {'[red]oui[/red]' if u.get('is_blocked') else 'non'}")
    if u.get("is_blocked"):
        rprint(f"  Raison  : {u.get('blocked_reason') or '–'}")
        rprint(f"  Jusqu'à : {_fmt_dt(u.get('blocked_until'))}")
    perms = u.get("permissions",{})
    rprint(f"  Sync    : {'✓' if perms.get('can_sync') else '✗'}")
    rprint(f"  Suppr.  : {'✓' if perms.get('can_delete') else '✗'}")
    rprint(f"  Refresh : {'✓' if perms.get('can_refresh') else '✗'}")
    quota = perms.get("quota",{})
    if quota.get("enabled"):
        rprint(f"  Quota   : {quota.get('max_syncs')} sync / {quota.get('period')}")
    rprint(f"  Groupes : {len(u.get('groups',[]))}")


@user_app.command(name="creer")
def user_creer(
    username: str           = typer.Argument(...),
    password: str           = typer.Argument(...),
    role:     str           = typer.Option("user", "--role", help="user|admin"),
    email:    Optional[str] = typer.Option(None,   "--email"),
):
    """Crée un nouvel utilisateur."""
    import db.user_repository as user_repo
    from api.dependencies import hash_password
    from models.user import Role

    async def _create():
        if await user_repo.find_by_username(username):
            rprint(f"[red]L'utilisateur '{username}' existe déjà.[/red]")
            raise typer.Exit(1)
        doc = {
            "username":        username,
            "email":           email,
            "role":            Role.ADMIN if role == "admin" else Role.USER,
            "hashed_password": hash_password(password),
            "is_active":       True,
            "is_blocked":      False,
            "groups":          [],
            "permissions": {
                "can_sync": False, "can_delete": False, "can_refresh": False,
                "allowed_catalogues": [], "catalogue_content": {},
                "quota": {"enabled": False, "period": "month", "max_syncs": 10},
            },
        }
        await user_repo.create_user(doc)

    _run(_create())
    rprint(f"[green]✓ Utilisateur '[bold]{username}[/bold]' créé (rôle : {role}).[/green]")


@user_app.command(name="supprimer")
def user_supprimer(username: str = typer.Argument(...)):
    """Supprime un utilisateur."""
    import db.user_repository as user_repo
    ok = _run(user_repo.delete_user(username))
    if not ok:
        rprint(f"[red]Utilisateur '{username}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"[green]✓ '{username}' supprimé.[/green]")


@user_app.command(name="bloquer")
def user_bloquer(
    username:  str           = typer.Argument(...),
    raison:    Optional[str] = typer.Option(None, "--raison"),
    jusqu_au:  Optional[str] = typer.Option(None, "--jusqu-au", help="Date ISO ex: 2026-12-31"),
):
    """Bloque un utilisateur (accès refusé)."""
    import db.user_repository as user_repo
    fields: dict = {"is_blocked": True, "blocked_reason": raison or ""}
    if jusqu_au:
        fields["blocked_until"] = jusqu_au
    ok = _run(user_repo.update_user(username, fields))
    if not ok:
        rprint(f"[red]'{username}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"[yellow]✓ '{username}' bloqué.[/yellow]")


@user_app.command(name="debloquer")
def user_debloquer(username: str = typer.Argument(...)):
    """Débloque un utilisateur."""
    import db.user_repository as user_repo
    ok = _run(user_repo.update_user(username, {
        "is_blocked": False, "blocked_reason": "", "blocked_until": None,
    }))
    if not ok:
        rprint(f"[red]'{username}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"[green]✓ '{username}' débloqué.[/green]")


@user_app.command(name="perms")
def user_perms(
    username: str            = typer.Argument(...),
    sync:     Optional[bool] = typer.Option(None, "--sync/--no-sync"),
    delete:   Optional[bool] = typer.Option(None, "--delete/--no-delete"),
    refresh:  Optional[bool] = typer.Option(None, "--refresh/--no-refresh"),
    download: Optional[bool] = typer.Option(None, "--download/--no-download"),
):
    """Modifie les permissions d'un utilisateur."""
    import db.user_repository as user_repo

    async def _update():
        u = await user_repo.find_by_username(username)
        if not u:
            rprint(f"[red]'{username}' introuvable.[/red]"); raise typer.Exit(1)
        perms = dict(u.get("permissions",{}))
        if sync     is not None: perms["can_sync"]     = sync
        if delete   is not None: perms["can_delete"]   = delete
        if refresh  is not None: perms["can_refresh"]  = refresh
        if download is not None: perms["can_download"] = download
        await user_repo.update_user(username, {"permissions": perms})

    _run(_update())
    rprint(f"[green]✓ Permissions de '{username}' mises à jour.[/green]")


@user_app.command(name="quota")
def user_quota(
    username:   str           = typer.Argument(...),
    max_syncs:  Optional[int] = typer.Option(None, "--max",     help="Limite de syncs"),
    periode:    Optional[str] = typer.Option(None, "--periode", help="day|month|year"),
    desactiver: bool          = typer.Option(False,"--desactiver"),
):
    """Configure le quota de synchronisation d'un utilisateur."""
    import db.user_repository as user_repo

    async def _update():
        u = await user_repo.find_by_username(username)
        if not u:
            rprint(f"[red]'{username}' introuvable.[/red]"); raise typer.Exit(1)
        perms = dict(u.get("permissions",{}))
        if desactiver:
            perms["quota"] = {"enabled": False, "period": "month", "max_syncs": 10}
        else:
            if max_syncs is None:
                rprint("[red]Précisez --max N ou --desactiver.[/red]"); raise typer.Exit(1)
            q = dict(perms.get("quota",{}))
            q["enabled"]   = True
            q["max_syncs"] = max_syncs
            if periode:
                q["period"] = periode
            perms["quota"] = q
        await user_repo.update_user(username, {"permissions": perms})

    _run(_update())
    if desactiver:
        rprint(f"[yellow]✓ Quota de '{username}' désactivé.[/yellow]")
    else:
        rprint(f"[green]✓ Quota de '{username}' : {max_syncs} sync / {periode or 'month'}.[/green]")


@user_app.command(name="groupes")
def user_groupes(username: str = typer.Argument(...)):
    """Liste les groupes d'un utilisateur."""
    import db.user_repository as user_repo
    import db.groups_repository as groups_repo

    async def _fetch():
        u = await user_repo.find_by_username(username)
        if not u:
            rprint(f"[red]'{username}' introuvable.[/red]"); raise typer.Exit(1)
        gids = u.get("groups",[])
        if not gids:
            rprint(f"[yellow]'{username}' n'appartient à aucun groupe.[/yellow]")
            return []
        return await groups_repo.find_by_ids([str(g) for g in gids])

    groups = _run(_fetch())
    if not groups:
        return
    table = Table(title=f"Groupes de {username}")
    table.add_column("ID")
    table.add_column("Nom", style="cyan")
    table.add_column("Type")
    for g in groups:
        table.add_row(g.get("id","?"), g.get("name","?"), g.get("type","?"))
    console.print(table)


# ══════════════════════════════════════════════════════════════════════════════
#  GROUPES
# ══════════════════════════════════════════════════════════════════════════════

@group_app.command(name="liste")
def group_liste():
    """Liste tous les groupes."""
    import db.groups_repository as groups_repo
    groups = _run(groups_repo.list_all())
    if not groups:
        rprint("[yellow]Aucun groupe.[/yellow]"); return
    table = Table(title=f"{len(groups)} groupe(s)")
    table.add_column("ID", style="dim")
    table.add_column("Nom", style="cyan")
    table.add_column("Type")
    table.add_column("Description")
    table.add_column("MAJ")
    for g in groups:
        table.add_row(
            g.get("id","?"), g.get("name","?"), g.get("type","?"),
            g.get("description") or "–",
            _fmt_dt(g.get("updated_at")),
        )
    console.print(table)


@group_app.command(name="get")
def group_get(group_id: str = typer.Argument(..., help="ID du groupe")):
    """Affiche le détail d'un groupe."""
    import db.groups_repository as groups_repo

    async def _fetch():
        g = await groups_repo.find_by_id(group_id)
        if not g:
            rprint(f"[red]Groupe '{group_id}' introuvable.[/red]"); raise typer.Exit(1)
        nb = await groups_repo.count_members(group_id)
        return g, nb

    g, nb = _run(_fetch())
    rprint(f"\n[bold cyan]{g.get('name')}[/bold cyan]  [dim]{g.get('type')}[/dim]")
    rprint(f"  ID          : {g.get('id')}")
    rprint(f"  Description : {g.get('description') or '–'}")
    if g.get("catalogue_slugs"):
        rprint(f"  Slugs       : {', '.join(g['catalogue_slugs'])}")
    if g.get("genres"):
        rprint(f"  Genres      : {', '.join(g['genres'])}")
    perms = g.get("permissions",{})
    rprint(f"  Sync/Del/Ref: {'✓' if perms.get('can_sync') else '✗'} / "
           f"{'✓' if perms.get('can_delete') else '✗'} / "
           f"{'✓' if perms.get('can_refresh') else '✗'}")
    rprint(f"  Téléchgt    : {'✓' if perms.get('can_download',True) else '✗'}")
    q = perms.get("download_quota",{})
    if q.get("enabled"):
        rprint(f"  DL quota    : {q.get('max_files_per_day')} fich./j · {q.get('max_gb_per_day')} Go/j")
    rprint(f"  Membres     : {nb}")


@group_app.command(name="creer")
def group_creer(
    nom:   str           = typer.Argument(...),
    type_: str           = typer.Option(..., "--type", help="catalogue|genre|permission"),
    desc:  Optional[str] = typer.Option(None, "--desc"),
):
    """Crée un nouveau groupe."""
    import db.groups_repository as groups_repo
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "name": nom, "type": type_, "description": desc,
        "catalogue_slugs": [], "catalogue_content": {}, "genres": [],
        "permissions": {
            "can_sync": False, "can_delete": False, "can_refresh": False,
            "can_download": True, "download_forbidden_slugs": [],
            "download_quota": {},
            "quota": {"enabled": False, "period": "month", "max_syncs": 10},
        },
        "created_at": now, "updated_at": now,
    }
    gid = _run(groups_repo.create(doc))
    rprint(f"[green]✓ Groupe '[bold]{nom}[/bold]' créé.[/green]  id={gid}")


@group_app.command(name="supprimer")
def group_supprimer(group_id: str = typer.Argument(...)):
    """Supprime un groupe."""
    import db.groups_repository as groups_repo
    ok = _run(groups_repo.delete(group_id))
    if not ok:
        rprint(f"[red]Groupe '{group_id}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"[green]✓ Groupe '{group_id}' supprimé.[/green]")


@group_app.command(name="membres")
def group_membres(group_id: str = typer.Argument(...)):
    """Liste les membres d'un groupe."""
    import db.groups_repository as groups_repo
    members = _run(groups_repo.list_members(group_id))
    if not members:
        rprint("[yellow]Aucun membre dans ce groupe.[/yellow]"); return
    table = Table(title=f"Membres du groupe {group_id}")
    table.add_column("Username", style="cyan")
    table.add_column("Email")
    table.add_column("Rôle")
    table.add_column("Actif", justify="center")
    for m in members:
        table.add_row(
            m.get("username","?"), m.get("email") or "–",
            m.get("role","?"), "✓" if m.get("is_active") else "✗",
        )
    console.print(table)


# ══════════════════════════════════════════════════════════════════════════════
#  APPLICATIONS API
# ══════════════════════════════════════════════════════════════════════════════

@app_app.command(name="liste")
def app_liste():
    """Liste les applications API."""
    import db.clients_repository as clients_repo
    clients = _run(clients_repo.list_clients())
    if not clients:
        rprint("[yellow]Aucune application.[/yellow]"); return
    table = Table(title=f"{len(clients)} application(s)")
    table.add_column("client_id", style="dim")
    table.add_column("Nom", style="cyan")
    table.add_column("Description")
    table.add_column("Actif", justify="center")
    table.add_column("Créé le")
    for c in clients:
        table.add_row(
            c.get("client_id","?"), c.get("name","?"),
            c.get("description") or "–",
            "✓" if c.get("is_active") else "✗",
            _fmt_dt(c.get("created_at")),
        )
    console.print(table)


@app_app.command(name="get")
def app_get(client_id: str = typer.Argument(...)):
    """Affiche le détail d'une application."""
    import db.clients_repository as clients_repo
    c = _run(clients_repo.find_by_client_id(client_id))
    if not c:
        rprint(f"[red]Application '{client_id}' introuvable.[/red]"); raise typer.Exit(1)
    c.pop("client_secret_hash", None)
    rprint(f"\n[bold cyan]{c.get('name')}[/bold cyan]")
    rprint(f"  client_id   : {c.get('client_id')}")
    rprint(f"  Description : {c.get('description') or '–'}")
    rprint(f"  Actif       : {'oui' if c.get('is_active') else 'non'}")
    rprint(f"  Créé le     : {_fmt_dt(c.get('created_at'))}")
    perms = c.get("permissions",{})
    if perms:
        rprint(f"  Sync/Del/Ref: {'✓' if perms.get('can_sync') else '✗'} / "
               f"{'✓' if perms.get('can_delete') else '✗'} / "
               f"{'✓' if perms.get('can_refresh') else '✗'}")


@app_app.command(name="creer")
def app_creer(
    nom:  str           = typer.Argument(..., help="Nom de l'application"),
    desc: Optional[str] = typer.Option(None, "--desc"),
):
    """Crée une nouvelle application API (le secret est affiché une seule fois)."""
    import db.clients_repository as clients_repo
    from api.dependencies import hash_password

    cid    = "cli_" + _secrets.token_urlsafe(16)
    plain  = _secrets.token_urlsafe(32)
    hashed = hash_password(plain)
    now    = datetime.now(timezone.utc).isoformat()
    doc    = {
        "client_id": cid, "client_secret_hash": hashed,
        "name": nom, "description": desc, "is_active": True,
        "permissions": {
            "can_sync": False, "can_delete": False, "can_refresh": False,
            "allowed_catalogues": [], "catalogue_content": {},
            "quota": {"enabled": False, "period": "month", "max_syncs": 10},
        },
        "created_at": now, "updated_at": now,
    }
    _run(clients_repo.create_client(doc))
    rprint(f"\n[green]✓ Application '[bold]{nom}[/bold]' créée.[/green]")
    rprint(f"  [bold]client_id[/bold]     : [cyan]{cid}[/cyan]")
    rprint(f"  [bold]client_secret[/bold] : [yellow]{plain}[/yellow]")
    rprint(f"\n[dim]Copiez le secret maintenant — il ne sera plus affiché.[/dim]\n")


@app_app.command(name="supprimer")
def app_supprimer(client_id: str = typer.Argument(...)):
    """Supprime une application."""
    import db.clients_repository as clients_repo
    ok = _run(clients_repo.delete_client(client_id))
    if not ok:
        rprint(f"[red]'{client_id}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"[green]✓ Application '{client_id}' supprimée.[/green]")


@app_app.command(name="activer")
def app_activer(client_id: str = typer.Argument(...)):
    """Active une application."""
    import db.clients_repository as clients_repo
    ok = _run(clients_repo.update_client(client_id, {"is_active": True}))
    if not ok:
        rprint(f"[red]'{client_id}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"[green]✓ '{client_id}' activée.[/green]")


@app_app.command(name="desactiver")
def app_desactiver(client_id: str = typer.Argument(...)):
    """Désactive une application (bloquée sans suppression)."""
    import db.clients_repository as clients_repo
    ok = _run(clients_repo.update_client(client_id, {"is_active": False}))
    if not ok:
        rprint(f"[red]'{client_id}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"[yellow]✓ '{client_id}' désactivée.[/yellow]")


@app_app.command(name="regenerer-secret")
def app_regenerer_secret(client_id: str = typer.Argument(...)):
    """Régénère le secret d'une application (invalide l'ancien)."""
    import db.clients_repository as clients_repo
    from api.dependencies import hash_password

    plain  = _secrets.token_urlsafe(32)
    hashed = hash_password(plain)
    ok = _run(clients_repo.update_client(client_id, {"client_secret_hash": hashed}))
    if not ok:
        rprint(f"[red]'{client_id}' introuvable.[/red]"); raise typer.Exit(1)
    rprint(f"\n[green]✓ Nouveau secret pour '{client_id}' :[/green]")
    rprint(f"  [bold]client_secret[/bold] : [yellow]{plain}[/yellow]")
    rprint(f"\n[dim]Copiez le secret maintenant — il ne sera plus affiché.[/dim]\n")


# ══════════════════════════════════════════════════════════════════════════════
#  SÉCURITÉ
# ══════════════════════════════════════════════════════════════════════════════

@security_app.command(name="statut")
def sec_statut():
    """Affiche l'état du verrou API et le nombre d'IPs bannies."""
    import services.api_guard as api_guard
    import db.ip_bans_repository as ip_bans_repo

    async def _fetch():
        await ip_bans_repo.load()
        await api_guard.load()
        return api_guard.get_state(), await ip_bans_repo.list_bans()

    state, bans = _run(_fetch())
    locked = state.get("locked", False)
    rprint(f"\nAPI          : {'[red]VERROUILLÉE[/red]' if locked else '[green]ouverte[/green]'}")
    if locked:
        rprint(f"Message      : {state.get('reason') or '–'}")
    rprint(f"IPs bannies  : {len(bans)}")
    rprint(f"\n[dim]Note : quand l'API est verrouillée, utilisateurs ET applications")
    rprint(f"reçoivent une erreur 503. Seuls les comptes admin peuvent passer.[/dim]")


@security_app.command(name="verrouiller")
def sec_verrouiller(
    raison: str = typer.Option("Maintenance en cours.", "--raison",
                               help="Message affiché aux utilisateurs/apps bloqués"),
):
    """Verrouille l'API pour tous les non-administrateurs (utilisateurs ET applications → 503)."""
    import services.api_guard as api_guard
    _run(api_guard.set_state(True, raison))
    rprint(f"[red]✓ API verrouillée.[/red]  Tous les non-admins (users + apps) reçoivent 503.")
    rprint(f"  Message : {raison}")


@security_app.command(name="deverrouiller")
def sec_deverrouiller():
    """Déverrouille l'API (accès normal restauré pour tous)."""
    import services.api_guard as api_guard
    _run(api_guard.set_state(False, ""))
    rprint("[green]✓ API déverrouillée — accès restauré.[/green]")


@security_app.command(name="bans")
def sec_bans():
    """Liste les adresses IP bannies."""
    import db.ip_bans_repository as ip_bans_repo

    async def _fetch():
        await ip_bans_repo.load()
        return await ip_bans_repo.list_bans()

    bans = _run(_fetch())
    if not bans:
        rprint("[yellow]Aucune IP bannie.[/yellow]"); return
    table = Table(title=f"{len(bans)} IP(s) bannie(s)")
    table.add_column("IP", style="cyan")
    table.add_column("Raison")
    table.add_column("Banni le")
    table.add_column("Par")
    for b in bans:
        table.add_row(
            b.get("ip","?"), b.get("reason") or "–",
            _fmt_dt(b.get("banned_at")), b.get("banned_by") or "–",
        )
    console.print(table)


@security_app.command(name="bannir")
def sec_bannir(
    ip:    str           = typer.Argument(..., help="Adresse IP à bannir"),
    raison: Optional[str] = typer.Option(None, "--raison"),
):
    """Bannit une adresse IP (toutes les requêtes de cette IP → 403)."""
    import db.ip_bans_repository as ip_bans_repo

    async def _ban():
        await ip_bans_repo.load()
        await ip_bans_repo.add_ban(ip, reason=raison or "", banned_by="cli")

    _run(_ban())
    rprint(f"[red]✓ IP '{ip}' bannie.[/red]")


@security_app.command(name="debannir")
def sec_debannir(ip: str = typer.Argument(...)):
    """Lève le ban d'une adresse IP."""
    import db.ip_bans_repository as ip_bans_repo

    async def _unban():
        await ip_bans_repo.load()
        return await ip_bans_repo.remove_ban(ip)

    ok = _run(_unban())
    if not ok:
        rprint(f"[yellow]'{ip}' n'était pas bannie.[/yellow]")
    else:
        rprint(f"[green]✓ IP '{ip}' débannie.[/green]")


# ══════════════════════════════════════════════════════════════════════════════
#  TÉLÉCHARGEMENTS
# ══════════════════════════════════════════════════════════════════════════════

@dl_app.command(name="historique")
def dl_historique(limit: int = typer.Option(50, "--limit", "-n", help="Nombre max de lignes")):
    """Affiche l'historique des téléchargements."""
    import db.downloads_repository as dl_repo
    items = _run(dl_repo.list_recent(limit=limit))
    if not items:
        rprint("[yellow]Aucun téléchargement enregistré.[/yellow]"); return
    table = Table(title=f"{len(items)} téléchargement(s) récents")
    table.add_column("Utilisateur", style="cyan")
    table.add_column("Slug")
    table.add_column("Fichier")
    table.add_column("Taille", justify="right")
    table.add_column("Date")
    for d in items:
        size = d.get("size_bytes", 0)
        size_str = f"{size/1024**2:.1f} Mo" if size else "–"
        table.add_row(
            d.get("username","?"), d.get("slug","?"),
            d.get("filename","?"), size_str,
            _fmt_dt(d.get("created_at")),
        )
    console.print(table)


@dl_app.command(name="quotas")
def dl_quotas():
    """Liste les quotas de téléchargement configurés."""
    import db.downloads_repository as dl_repo
    quotas = _run(dl_repo.list_quotas())
    if not quotas:
        rprint("[yellow]Aucun quota configuré.[/yellow]"); return
    table = Table(title=f"{len(quotas)} quota(s)")
    table.add_column("Utilisateur", style="cyan")
    table.add_column("Max fichiers/j", justify="right")
    table.add_column("Max Go/j", justify="right")
    table.add_column("Actif", justify="center")
    for q in quotas:
        table.add_row(
            q.get("username","?"),
            str(q.get("max_files_per_day","–")),
            str(q.get("max_gb_per_day","–")),
            "✓" if q.get("enabled") else "✗",
        )
    console.print(table)


@dl_app.command(name="quota-set")
def dl_quota_set(
    username:     str   = typer.Argument(...),
    max_fichiers: int   = typer.Option(..., "--max-fichiers", help="Fichiers max par jour"),
    max_go:       float = typer.Option(..., "--max-go",       help="Gigaoctets max par jour"),
    desactiver:   bool  = typer.Option(False, "--desactiver"),
):
    """Configure le quota de téléchargement d'un utilisateur."""
    import db.downloads_repository as dl_repo
    _run(dl_repo.set_quota(
        username=username,
        max_files_per_day=max_fichiers,
        max_gb_per_day=max_go,
        can_download=not desactiver,
    ))
    if desactiver:
        rprint(f"[yellow]✓ Quota de '{username}' désactivé.[/yellow]")
    else:
        rprint(f"[green]✓ Quota de '{username}' : {max_fichiers} fichiers / {max_go} Go par jour.[/green]")


@dl_app.command(name="quota-supprimer")
def dl_quota_supprimer(username: str = typer.Argument(...)):
    """Supprime le quota de téléchargement d'un utilisateur."""
    import db.downloads_repository as dl_repo
    ok = _run(dl_repo.delete_quota(username))
    if not ok:
        rprint(f"[yellow]Aucun quota trouvé pour '{username}'.[/yellow]")
    else:
        rprint(f"[green]✓ Quota de '{username}' supprimé.[/green]")


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app()
