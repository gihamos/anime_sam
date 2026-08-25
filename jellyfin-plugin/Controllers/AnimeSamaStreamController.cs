using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace Jellyfin.Plugin.AnimeSama.Controllers;

/// <summary>
/// Résout une ou plusieurs URLs embed anime-sama en flux lisible par Jellyfin.
///
/// Certaines sources (ex. Sibnet) exigent un header Referer/Origin/Cookie précis —
/// une simple redirection HTTP 302 les perd, donc ce contrôleur proxifie réellement
/// les octets (et réécrit les playlists HLS .m3u8 pour que les segments passent
/// aussi par le proxy avec les mêmes headers).
///
///   GET /AnimeSama/stream?url=...&url=...   → résout (avec fallback) puis redirige vers /proxy
///   GET /AnimeSama/proxy?target=...&ref=...&origin=...&cookie=...   → proxy d'octets/playlist
/// </summary>
[ApiController]
[Route("AnimeSama")]
public class AnimeSamaStreamController : ControllerBase
{
    private static readonly HttpClient Http = new(new HttpClientHandler { AllowAutoRedirect = false })
    {
        Timeout = TimeSpan.FromSeconds(30),
    };

    [HttpGet("stream")]
    public async Task<IActionResult> ResolveStream([FromQuery] List<string> url, CancellationToken ct)
    {
        if (url is null || url.Count == 0)
            return BadRequest("Paramètre 'url' manquant.");

        var client = Plugin.Instance?.ApiClient;
        if (client is null)
            return StatusCode(503, "Plugin Anime Sama non initialisé.");

        var stream = await client.ResolveStreamWithFallbackAsync(url, ct).ConfigureAwait(false);
        if (stream?.Url is null)
            return NotFound("Impossible de résoudre le flux — toutes les sources ont échoué.");

        // Préférer le proxy du serveur Anime Sama (même IP/session que la résolution) : des
        // sources comme Vidzy lient l'URL signée à l'IP qui l'a obtenue, donc un fetch direct
        // depuis Jellyfin échoue en 403 même avec les bons headers Referer/Origin, alors que ce
        // proxy — hébergé sur le serveur qui a fait la résolution — passe toujours.
        if (!string.IsNullOrEmpty(stream.ProxyUrl))
        {
            var apiUrl = Plugin.Instance?.Configuration.ApiUrl?.TrimEnd('/') ?? string.Empty;
            if (!string.IsNullOrEmpty(apiUrl))
                return Redirect($"{apiUrl}{stream.ProxyUrl}");
        }

        stream.Headers.TryGetValue("Referer", out var referer);
        stream.Headers.TryGetValue("Origin",  out var origin);
        stream.Headers.TryGetValue("Cookie",  out var cookie);

        return Redirect(BuildProxyPath(stream.Url, referer, origin, cookie));
    }

    [HttpGet("proxy")]
    public async Task Proxy(
        [FromQuery] string target,
        [FromQuery] string? referer,
        [FromQuery] string? origin,
        [FromQuery] string? cookie,
        CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, target);
        if (!string.IsNullOrEmpty(referer)) req.Headers.TryAddWithoutValidation("Referer", referer);
        if (!string.IsNullOrEmpty(origin))  req.Headers.TryAddWithoutValidation("Origin", origin);
        if (!string.IsNullOrEmpty(cookie))  req.Headers.TryAddWithoutValidation("Cookie", cookie);
        if (Request.Headers.TryGetValue("Range", out var range))
            req.Headers.TryAddWithoutValidation("Range", (string?)range);
        req.Headers.TryAddWithoutValidation("User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36");

        HttpResponseMessage upstream;
        try
        {
            upstream = await Http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct).ConfigureAwait(false);
        }
        catch
        {
            Response.StatusCode = 502;
            return;
        }

        // Le lecteur source redirige encore — suivre manuellement en conservant les headers
        if ((int)upstream.StatusCode is >= 300 and < 400 && upstream.Headers.Location is not null)
        {
            var next = upstream.Headers.Location.IsAbsoluteUri
                ? upstream.Headers.Location.ToString()
                : new Uri(new Uri(target), upstream.Headers.Location).ToString();
            Response.Redirect(BuildProxyPath(next, referer, origin, cookie));
            return;
        }

        var contentType = upstream.Content.Headers.ContentType?.MediaType ?? "application/octet-stream";
        // Ne traiter comme playlist que si la requête a réellement réussi — sinon une page
        // d'erreur HTML (403/404 amont) serait réécrite comme si c'était du HLS valide,
        // produisant un flux syntaxiquement correct mais qui ne joue jamais.
        bool isPlaylist = upstream.IsSuccessStatusCode
                       && (contentType.Contains("mpegurl", StringComparison.OrdinalIgnoreCase)
                           || target.Contains(".m3u8", StringComparison.OrdinalIgnoreCase));

        Response.StatusCode = (int)upstream.StatusCode;

        if (isPlaylist)
        {
            var text = await upstream.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            var rewritten = RewritePlaylist(text, target, referer, origin, cookie);
            Response.ContentType = "application/vnd.apple.mpegurl";
            await Response.WriteAsync(rewritten, Encoding.UTF8, ct).ConfigureAwait(false);
            return;
        }

        Response.ContentType = contentType;
        if (upstream.Content.Headers.ContentLength.HasValue)
            Response.ContentLength = upstream.Content.Headers.ContentLength;
        if (upstream.Headers.AcceptRanges.Count > 0)
            Response.Headers.AcceptRanges = string.Join(", ", upstream.Headers.AcceptRanges);
        if (upstream.Content.Headers.ContentRange is not null)
            Response.Headers["Content-Range"] = upstream.Content.Headers.ContentRange.ToString();

        var bodyStream = await upstream.Content.ReadAsStreamAsync(ct).ConfigureAwait(false);
        await using (bodyStream.ConfigureAwait(false))
        {
            await bodyStream.CopyToAsync(Response.Body, ct).ConfigureAwait(false);
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static string BuildProxyPath(string target, string? referer, string? origin, string? cookie)
    {
        var sb = new StringBuilder("/AnimeSama/proxy?target=").Append(Uri.EscapeDataString(target));
        if (!string.IsNullOrEmpty(referer)) sb.Append("&referer=").Append(Uri.EscapeDataString(referer));
        if (!string.IsNullOrEmpty(origin))  sb.Append("&origin=").Append(Uri.EscapeDataString(origin));
        if (!string.IsNullOrEmpty(cookie))  sb.Append("&cookie=").Append(Uri.EscapeDataString(cookie));
        return sb.ToString();
    }

    private static readonly Regex UriAttr = new("URI=\"([^\"]+)\"", RegexOptions.Compiled);

    /// <summary>Réécrit les lignes d'URI d'une playlist HLS pour qu'elles repassent par le proxy.</summary>
    private static string RewritePlaylist(string text, string baseUrl, string? referer, string? origin, string? cookie)
    {
        var baseUri = new Uri(baseUrl);
        string Resolve(string raw) => Uri.TryCreate(raw, UriKind.Absolute, out var abs)
            ? abs.ToString()
            : new Uri(baseUri, raw).ToString();

        var lines = text.Split('\n');
        for (int i = 0; i < lines.Length; i++)
        {
            var line = lines[i].TrimEnd('\r');

            if (line.StartsWith('#'))
            {
                // #EXT-X-KEY / #EXT-X-MAP contiennent une URI="..." à réécrire aussi
                if (line.Contains("URI=\""))
                {
                    lines[i] = UriAttr.Replace(line, m =>
                        $"URI=\"{BuildProxyPath(Resolve(m.Groups[1].Value), referer, origin, cookie)}\"");
                }
                continue;
            }

            if (string.IsNullOrWhiteSpace(line)) continue;

            lines[i] = BuildProxyPath(Resolve(line), referer, origin, cookie);
        }

        return string.Join('\n', lines);
    }
}
