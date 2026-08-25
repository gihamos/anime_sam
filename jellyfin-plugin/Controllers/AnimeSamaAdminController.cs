using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.AnimeSama.Api;
using MediaBrowser.Common.Api;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Jellyfin.Plugin.AnimeSama.Controllers;

[ApiController]
[Authorize(Policy = Policies.RequiresElevation)]
[Route("AnimeSama/admin")]
public class AnimeSamaAdminController : ControllerBase
{
    [HttpGet("search")]
    public async Task<IActionResult> Search(
        [FromQuery] string?  q         = null,
        [FromQuery] string?  type      = null,
        [FromQuery] string?  langue    = null,
        [FromQuery] string?  statut    = null,
        [FromQuery] string?  genre     = null,
        [FromQuery] int?     anneeMin  = null,
        [FromQuery] int?     anneeMax  = null,
        [FromQuery] int?     epsMin    = null,
        [FromQuery] int?     epsMax    = null,
        [FromQuery] int      page      = 1,
        CancellationToken    ct        = default)
    {
        var client = Plugin.Instance?.ApiClient;
        if (client is null) return StatusCode(503, "Plugin non initialisé.");

        var results = await client.SearchSiteAsync(
            q, type, langue, statut, genre, anneeMin, anneeMax, epsMin, epsMax, page, ct
        ).ConfigureAwait(false);

        return Ok(results);
    }

    [HttpPost("sync-content")]
    public async Task<IActionResult> SyncContent([FromQuery] string slug, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(slug))
            return BadRequest("Paramètre 'slug' manquant.");

        var client = Plugin.Instance?.ApiClient;
        if (client is null) return StatusCode(503, "Plugin non initialisé.");

        var catalogue = await client.EnsureCatalogueAsync(slug, ct).ConfigureAwait(false);
        if (catalogue is null) return NotFound($"Catalogue '{slug}' introuvable sur anime-sama.to.");

        var started = await client.TriggerSyncContentAsync(slug, ct).ConfigureAwait(false);
        if (started is null) return StatusCode(502, "Échec du démarrage de la synchronisation.");

        return Ok(started);
    }

    [HttpGet("sync-content/status")]
    public async Task<IActionResult> SyncContentStatus([FromQuery] string slug, CancellationToken ct)
    {
        var client = Plugin.Instance?.ApiClient;
        if (client is null) return StatusCode(503, "Plugin non initialisé.");

        var status = await client.GetSyncStatusAsync(slug, ct).ConfigureAwait(false);
        if (status is null) return NotFound();
        return Ok(status);
    }

    // ── Genres (anime-sama.to + TMDB) — pour le sélecteur de la recherche unifiée ──

    [HttpGet("genres")]
    public async Task<IActionResult> Genres([FromQuery] string source, CancellationToken ct)
    {
        var client = Plugin.Instance?.ApiClient;
        if (client is null) return StatusCode(503, "Plugin non initialisé.");

        if (source == "tmdb")
        {
            var tmdbGenres = await client.GetTmdbGenresAsync(ct).ConfigureAwait(false);
            return Ok(tmdbGenres ?? new TmdbGenresResponse());
        }

        var genres = await client.GetAnimeSamaGenresAsync(ct).ConfigureAwait(false);
        return Ok(genres);
    }

    // ── Films & séries (TMDB + Vidzy — source indépendante d'anime-sama.to) ────

    [HttpGet("tmdb-search")]
    public async Task<IActionResult> TmdbSearch(
        [FromQuery] string?  q         = null,
        [FromQuery] string?  type      = null,
        [FromQuery] string?  genre     = null,
        [FromQuery] int?     anneeMin  = null,
        [FromQuery] int?     anneeMax  = null,
        [FromQuery] string?  pays      = null,
        [FromQuery] int      page      = 1,
        CancellationToken    ct        = default)
    {
        if (string.IsNullOrWhiteSpace(q) && string.IsNullOrWhiteSpace(genre)
            && !anneeMin.HasValue && !anneeMax.HasValue && string.IsNullOrWhiteSpace(pays))
            return BadRequest("Fournir un titre (q) ou au moins un filtre (genre, anneeMin, anneeMax, pays).");

        var client = Plugin.Instance?.ApiClient;
        if (client is null) return StatusCode(503, "Plugin non initialisé.");

        var results = await client.SearchTmdbAsync(q, type, genre, anneeMin, anneeMax, pays, page, ct).ConfigureAwait(false);
        return Ok(results);
    }

    [HttpPost("tmdb-add")]
    public async Task<IActionResult> TmdbAdd(
        [FromQuery] string mediaType,
        [FromQuery] int    tmdbId,
        CancellationToken  ct = default)
    {
        if (mediaType != "movie" && mediaType != "tv")
            return BadRequest("Paramètre 'mediaType' doit être 'movie' ou 'tv'.");

        var client = Plugin.Instance?.ApiClient;
        if (client is null) return StatusCode(503, "Plugin non initialisé.");

        var catalogue = await client.AddFromTmdbAsync(mediaType, tmdbId, ct).ConfigureAwait(false);
        if (catalogue is null) return StatusCode(502, $"Échec de l'ajout de {mediaType}/{tmdbId} depuis TMDB.");

        return Ok(catalogue);
    }
}
