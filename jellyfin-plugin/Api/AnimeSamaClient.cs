using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Threading;
using System.Threading.Tasks;

namespace Jellyfin.Plugin.AnimeSama.Api;

public class AnimeSamaClient
{
    private readonly HttpClient _http;
    private readonly Func<PluginConfiguration> _getConfig;

    private string _token = string.Empty;
    private DateTime _tokenExpiry = DateTime.MinValue;

    public AnimeSamaClient(Func<PluginConfiguration> getConfig)
    {
        _getConfig = getConfig;
        _http = new HttpClient { Timeout = TimeSpan.FromSeconds(60) };
    }

    // ── Auth ──────────────────────────────────────────────────────────────────

    private async Task EnsureAuthAsync(CancellationToken ct)
    {
        if (!string.IsNullOrEmpty(_token) && DateTime.UtcNow < _tokenExpiry)
            return;

        var config = _getConfig();

        if (string.IsNullOrWhiteSpace(config.ApiUrl) || string.IsNullOrWhiteSpace(config.Username))
            throw new InvalidOperationException(
                "Plugin Anime Sama non configuré. Renseignez l'URL et les identifiants dans Tableau de bord → Plugins → Anime Sama.");

        // OAuth2PasswordRequestForm attend application/x-www-form-urlencoded
        var form = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["username"] = config.Username,
            ["password"] = config.Password,
        });

        var resp = await _http.PostAsync(
            $"{config.ApiUrl.TrimEnd('/')}/auth/login",
            form,
            ct).ConfigureAwait(false);

        resp.EnsureSuccessStatusCode();

        var login = await resp.Content
            .ReadFromJsonAsync<LoginResponse>(cancellationToken: ct)
            .ConfigureAwait(false);

        _token = login?.AccessToken
            ?? throw new InvalidOperationException("Réponse de login invalide (access_token absent).");

        _tokenExpiry = DateTime.UtcNow.AddMinutes(config.TokenExpiryMinutes);
    }

    private async Task<HttpResponseMessage> GetAsync(string path, CancellationToken ct)
    {
        await EnsureAuthAsync(ct).ConfigureAwait(false);
        var config = _getConfig();

        using var req = new HttpRequestMessage(HttpMethod.Get, $"{config.ApiUrl.TrimEnd('/')}{path}");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _token);

        return await _http.SendAsync(req, ct).ConfigureAwait(false);
    }

    private async Task<HttpResponseMessage> PostAsync(string path, object? body, CancellationToken ct)
    {
        await EnsureAuthAsync(ct).ConfigureAwait(false);
        var config = _getConfig();

        using var req = new HttpRequestMessage(HttpMethod.Post, $"{config.ApiUrl.TrimEnd('/')}{path}");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _token);
        if (body is not null)
            req.Content = JsonContent.Create(body);

        return await _http.SendAsync(req, ct).ConfigureAwait(false);
    }

    // ── Catalogue ─────────────────────────────────────────────────────────────

    public async Task<(List<CatalogueSummary> Items, int Total)> GetCataloguesAsync(
        int skip, int limit, CancellationToken ct)
    {
        var resp = await GetAsync($"/mycatalogues/?skip={skip}&limit={limit}", ct).ConfigureAwait(false);
        resp.EnsureSuccessStatusCode();

        int total = 0;
        if (resp.Headers.TryGetValues("X-Total-Count", out var vals))
            int.TryParse(System.Linq.Enumerable.FirstOrDefault(vals), out total);

        var items = await resp.Content
            .ReadFromJsonAsync<List<CatalogueSummary>>(cancellationToken: ct)
            .ConfigureAwait(false) ?? new List<CatalogueSummary>();

        if (total == 0) total = items.Count;
        return (items, total);
    }

    public async Task<List<CatalogueSummary>> GetAllCataloguesAsync(CancellationToken ct)
    {
        var all = new List<CatalogueSummary>();
        const int pageSize = 100;
        int skip = 0;

        while (true)
        {
            var (items, total) = await GetCataloguesAsync(skip, pageSize, ct).ConfigureAwait(false);
            all.AddRange(items);
            skip += items.Count;
            if (items.Count == 0 || skip >= total) break;
        }

        return all;
    }

    public async Task<CatalogueDetail?> GetCatalogueAsync(string slug, CancellationToken ct)
    {
        var resp = await GetAsync($"/catalogues/{slug}", ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content
            .ReadFromJsonAsync<CatalogueDetail>(cancellationToken: ct)
            .ConfigureAwait(false);
    }

    // ── Stream ────────────────────────────────────────────────────────────────

    public async Task<StreamResolveResponse?> ResolveStreamAsync(string embedUrl, CancellationToken ct)
    {
        var encoded = Uri.EscapeDataString(embedUrl);
        var resp = await GetAsync($"/api/stream/resolve?url={encoded}", ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content
            .ReadFromJsonAsync<StreamResolveResponse>(cancellationToken: ct)
            .ConfigureAwait(false);
    }

    /// <summary>Essaie chaque URL candidate dans l'ordre, retourne la première qui se résout.</summary>
    public async Task<StreamResolveResponse?> ResolveStreamWithFallbackAsync(
        IEnumerable<string> embedUrls, CancellationToken ct)
    {
        foreach (var url in embedUrls)
        {
            ct.ThrowIfCancellationRequested();
            try
            {
                var result = await ResolveStreamAsync(url, ct).ConfigureAwait(false);
                if (result?.Url is not null) return result;
            }
            catch (OperationCanceledException) { throw; }
            catch { /* on tente la source suivante */ }
        }
        return null;
    }

    // ── Recherche / Admin ────────────────────────────────────────────────────

    public async Task<List<SiteSearchResult>> SearchSiteAsync(
        string?  query    = null,
        string?  type     = null,
        string?  langue   = null,
        string?  statut   = null,
        string?  genre    = null,
        int?     anneeMin = null,
        int?     anneeMax = null,
        int?     epsMin   = null,
        int?     epsMax   = null,
        int      page     = 1,
        CancellationToken ct = default)
    {
        var qs = new System.Text.StringBuilder("/catalogues/site/rechercher?page=").Append(page);
        if (!string.IsNullOrWhiteSpace(query))   qs.Append("&search=").Append(Uri.EscapeDataString(query));
        if (!string.IsNullOrWhiteSpace(type))    qs.Append("&type=").Append(Uri.EscapeDataString(type));
        if (!string.IsNullOrWhiteSpace(langue))  qs.Append("&langue=").Append(Uri.EscapeDataString(langue));
        if (!string.IsNullOrWhiteSpace(statut))  qs.Append("&statut=").Append(Uri.EscapeDataString(statut));
        if (!string.IsNullOrWhiteSpace(genre))   qs.Append("&genre=").Append(Uri.EscapeDataString(genre));
        if (anneeMin.HasValue) qs.Append("&annee_min=").Append(anneeMin);
        if (anneeMax.HasValue) qs.Append("&annee_max=").Append(anneeMax);
        if (epsMin.HasValue)   qs.Append("&episodes_min=").Append(epsMin);
        if (epsMax.HasValue)   qs.Append("&episodes_max=").Append(epsMax);

        var resp = await GetAsync(qs.ToString(), ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return new List<SiteSearchResult>();
        return await resp.Content
            .ReadFromJsonAsync<List<SiteSearchResult>>(cancellationToken: ct)
            .ConfigureAwait(false) ?? new List<SiteSearchResult>();
    }

    /// <summary>Force le scrape de la structure du catalogue s'il n'est pas déjà en DB.</summary>
    public async Task<CatalogueDetail?> EnsureCatalogueAsync(string slug, CancellationToken ct)
        => await GetCatalogueAsync(slug, ct).ConfigureAwait(false);

    // ── Films & séries (TMDB + Vidzy) ────────────────────────────────────────

    /// <summary>Recherche TMDB — `mediaType` : "movie" | "tv" | null (recherche les deux).</summary>
    public async Task<List<TmdbSearchResult>> SearchTmdbAsync(string query, string? mediaType, CancellationToken ct)
    {
        var qs = $"/catalogues/tmdb/rechercher?q={System.Uri.EscapeDataString(query)}";
        if (!string.IsNullOrWhiteSpace(mediaType)) qs += $"&type={mediaType}";

        var resp = await GetAsync(qs, ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return new List<TmdbSearchResult>();
        return await resp.Content
            .ReadFromJsonAsync<List<TmdbSearchResult>>(cancellationToken: ct)
            .ConfigureAwait(false) ?? new List<TmdbSearchResult>();
    }

    /// <summary>Ajoute un film/série au catalogue depuis TMDB (structure + lecteur Vidzy).</summary>
    public async Task<CatalogueDetail?> AddFromTmdbAsync(string mediaType, int tmdbId, CancellationToken ct)
    {
        var resp = await PostAsync($"/catalogues/tmdb/{mediaType}/{tmdbId}", null, ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content
            .ReadFromJsonAsync<CatalogueDetail>(cancellationToken: ct)
            .ConfigureAwait(false);
    }

    public async Task<SyncStarted?> TriggerSyncContentAsync(string slug, CancellationToken ct)
    {
        var resp = await PostAsync($"/catalogues/{slug}/sync-content", null, ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content
            .ReadFromJsonAsync<SyncStarted>(cancellationToken: ct)
            .ConfigureAwait(false);
    }

    public async Task<SyncStatusResponse?> GetSyncStatusAsync(string slug, CancellationToken ct)
    {
        var resp = await GetAsync($"/catalogues/{slug}/sync-content/status", ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content
            .ReadFromJsonAsync<SyncStatusResponse>(cancellationToken: ct)
            .ConfigureAwait(false);
    }

    // ── Téléchargement ───────────────────────────────────────────────────────

    public async Task<JobCreated?> CreateEpisodeDownloadJobAsync(
        string slug, int saisonIdx, int episodeNum, CancellationToken ct)
    {
        var body = new { slug, saison_idx = saisonIdx, nums = new[] { episodeNum } };
        var resp = await PostAsync("/api/download/jobs", body, ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content
            .ReadFromJsonAsync<JobCreated>(cancellationToken: ct)
            .ConfigureAwait(false);
    }

    public async Task<JobCreated?> CreateFilmDownloadJobAsync(string slug, int filmIdx, CancellationToken ct)
    {
        var body = new { slug, film_idx = filmIdx };
        var resp = await PostAsync("/api/download/jobs", body, ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content
            .ReadFromJsonAsync<JobCreated>(cancellationToken: ct)
            .ConfigureAwait(false);
    }

    public async Task<JobStatus?> GetJobStatusAsync(string jobId, CancellationToken ct)
    {
        var resp = await GetAsync($"/api/download/jobs/{jobId}", ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content
            .ReadFromJsonAsync<JobStatus>(cancellationToken: ct)
            .ConfigureAwait(false);
    }

    /// <summary>Attend qu'un job de téléchargement soit prêt puis le sauvegarde sur disque.</summary>
    public async Task<bool> DownloadJobToFileAsync(
        string jobId, string destPath, CancellationToken ct, TimeSpan? timeout = null)
    {
        var deadline = DateTime.UtcNow + (timeout ?? TimeSpan.FromMinutes(15));

        while (DateTime.UtcNow < deadline)
        {
            ct.ThrowIfCancellationRequested();
            var status = await GetJobStatusAsync(jobId, ct).ConfigureAwait(false);
            if (status is null) return false;

            if (status.Status == "error") return false;
            if (status.Status == "ready" || status.Ready) break;

            await Task.Delay(TimeSpan.FromSeconds(2), ct).ConfigureAwait(false);
        }

        var fileResp = await GetAsync($"/api/download/jobs/{jobId}/file", ct).ConfigureAwait(false);
        if (!fileResp.IsSuccessStatusCode) return false;

        await using var fs = File.Create(destPath);
        await fileResp.Content.CopyToAsync(fs, ct).ConfigureAwait(false);
        return true;
    }
}
