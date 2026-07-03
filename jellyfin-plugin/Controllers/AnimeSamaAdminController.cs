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
}
