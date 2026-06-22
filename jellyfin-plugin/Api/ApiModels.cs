using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Jellyfin.Plugin.AnimeSama.Api;

// ── Auth ─────────────────────────────────────────────────────────────────────

public class LoginRequest
{
    [JsonPropertyName("username")]
    public string Username { get; set; } = string.Empty;

    [JsonPropertyName("password")]
    public string Password { get; set; } = string.Empty;
}

public class LoginResponse
{
    [JsonPropertyName("access_token")]
    public string AccessToken { get; set; } = string.Empty;
}

// ── Catalogue ─────────────────────────────────────────────────────────────────

public class CatalogueSummary
{
    [JsonPropertyName("slug")]
    public string Slug { get; set; } = string.Empty;

    [JsonPropertyName("titre")]
    public string Titre { get; set; } = string.Empty;

    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;

    [JsonPropertyName("image")]
    public string? Image { get; set; }

    [JsonPropertyName("synopsis")]
    public string? Synopsis { get; set; }

    [JsonPropertyName("annee")]
    public int? Annee { get; set; }

    [JsonPropertyName("statut")]
    public string? Statut { get; set; }

    [JsonPropertyName("genres")]
    public List<string> Genres { get; set; } = new();
}

public class CatalogueDetail : CatalogueSummary
{
    [JsonPropertyName("saisons")]
    public List<Saison> Saisons { get; set; } = new();

    [JsonPropertyName("films")]
    public List<Film> Films { get; set; } = new();
}

public class Saison
{
    [JsonPropertyName("nom")]
    public string Nom { get; set; } = string.Empty;

    [JsonPropertyName("langues_disponibles")]
    public List<string> LanguesDisponibles { get; set; } = new();

    // Épisodes groupés par langue : { "vf": [...], "vostfr": [...] }
    // Si l'API retourne une structure différente, ajuster ici.
    [JsonPropertyName("episodes")]
    public Dictionary<string, List<Episode>> Episodes { get; set; } = new();
}

public class Episode
{
    [JsonPropertyName("num")]
    public int Num { get; set; }

    [JsonPropertyName("titre")]
    public string? Titre { get; set; }

    [JsonPropertyName("player_url")]
    public string? PlayerUrl { get; set; }
}

public class Film
{
    [JsonPropertyName("titre")]
    public string? Titre { get; set; }

    [JsonPropertyName("player_url")]
    public string? PlayerUrl { get; set; }

    [JsonPropertyName("lang")]
    public string? Lang { get; set; }

    [JsonPropertyName("image")]
    public string? Image { get; set; }
}

// ── Stream ────────────────────────────────────────────────────────────────────

public class StreamResolveResponse
{
    [JsonPropertyName("url")]
    public string? Url { get; set; }

    [JsonPropertyName("audio_url")]
    public string? AudioUrl { get; set; }

    [JsonPropertyName("ext")]
    public string Ext { get; set; } = "mp4";

    [JsonPropertyName("protocol")]
    public string Protocol { get; set; } = "https";

    // Headers HTTP requis par la source (ex: Referer pour Sibnet)
    [JsonPropertyName("headers")]
    public Dictionary<string, string> Headers { get; set; } = new();

    [JsonPropertyName("title")]
    public string? Title { get; set; }

    [JsonPropertyName("duration")]
    public int? Duration { get; set; }

    [JsonPropertyName("merged")]
    public bool Merged { get; set; }
}
