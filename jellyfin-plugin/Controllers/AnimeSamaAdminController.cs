using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.AnimeSama.Api;
using MediaBrowser.Common.Api;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Jellyfin.Plugin.AnimeSama.Controllers;

/// <summary>
/// Recherche d'animés sur anime-sama.to et déclenchement de la synchronisation
/// du contenu (épisodes), exposés depuis la page de configuration du plugin.
/// [Authorize(Policy = "RequiresElevation")] restreint l'accès aux administrateurs Jellyfin.
/// </summary>
[ApiController]
[Authorize(Policy = Policies.RequiresElevation)]
[Route("AnimeSama/admin")]
public class AnimeSamaAdminController : ControllerBase
{
    [HttpGet("search")]
    public async Task<IActionResult> Search([FromQuery] string q, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(q))
            return BadRequest("Paramètre 'q' manquant.");

        var client = Plugin.Instance?.ApiClient;
        if (client is null) return StatusCode(503, "Plugin non initialisé.");

        var results = await client.SearchSiteAsync(q, ct).ConfigureAwait(false);
        return Ok(results);
    }

    [HttpPost("sync-content")]
    public async Task<IActionResult> SyncContent([FromQuery] string slug, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(slug))
            return BadRequest("Paramètre 'slug' manquant.");

        var client = Plugin.Instance?.ApiClient;
        if (client is null) return StatusCode(503, "Plugin non initialisé.");

        // Force le scrape de la structure si le catalogue n'est pas encore en DB
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
}
