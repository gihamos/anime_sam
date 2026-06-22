using System;
using System.Collections.Generic;
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

        var resp = await _http.PostAsJsonAsync(
            $"{config.ApiUrl.TrimEnd('/')}/auth/login",
            new LoginRequest { Username = config.Username, Password = config.Password },
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

    // ── Catalogue ─────────────────────────────────────────────────────────────

    public async Task<List<CatalogueSummary>> GetCataloguesAsync(CancellationToken ct)
    {
        var resp = await GetAsync("/catalogues/", ct).ConfigureAwait(false);
        resp.EnsureSuccessStatusCode();
        return await resp.Content
            .ReadFromJsonAsync<List<CatalogueSummary>>(cancellationToken: ct)
            .ConfigureAwait(false) ?? new List<CatalogueSummary>();
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
}
