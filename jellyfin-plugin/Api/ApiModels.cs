using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Jellyfin.Plugin.AnimeSama.Api;

// ── Auth ─────────────────────────────────────────────────────────────────────

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

    // L'API retourne "nom", pas "titre"
    [JsonPropertyName("nom")]
    public string Titre { get; set; } = string.Empty;

    [JsonPropertyName("type_contenu")]
    public string Type { get; set; } = string.Empty;

    [JsonPropertyName("image")]
    public string? Image { get; set; }

    [JsonPropertyName("synopsis")]
    public string? Synopsis { get; set; }

    [JsonPropertyName("annee")]
    public int? Annee { get; set; }

    [JsonPropertyName("etat")]
    public string? Statut { get; set; }

    [JsonPropertyName("genres")]
    public List<string> Genres { get; set; } = new();

    [JsonPropertyName("episodes_synced")]
    public bool EpisodesSynced { get; set; }
}

public class CatalogueDetail : CatalogueSummary
{
    [JsonPropertyName("saisons")]
    public List<Saison> Saisons { get; set; } = new();

    [JsonPropertyName("films")]
    public List<Film> Films { get; set; } = new();

    [JsonPropertyName("scans")]
    public List<Scan> Scans { get; set; } = new();
}

// Une saison = une entrée par langue (lang est un string, pas une liste)
public class Saison
{
    [JsonPropertyName("nom")]
    public string Nom { get; set; } = string.Empty;

    [JsonPropertyName("slug")]
    public string Slug { get; set; } = string.Empty;

    [JsonPropertyName("lang")]
    public string Lang { get; set; } = string.Empty;

    [JsonPropertyName("image")]
    public string? Image { get; set; }

    [JsonPropertyName("total_episodes")]
    public int TotalEpisodes { get; set; }

    [JsonPropertyName("episodes")]
    public List<Episode> Episodes { get; set; } = new();
}

public class Episode
{
    [JsonPropertyName("numero")]
    public int Numero { get; set; }

    [JsonPropertyName("titre")]
    public string? Titre { get; set; }

    [JsonPropertyName("videos")]
    public List<VideoSource> Videos { get; set; } = new();
}

public class VideoSource
{
    [JsonPropertyName("lecteur")]
    public string Lecteur { get; set; } = string.Empty;

    [JsonPropertyName("player_url")]
    public string? PlayerUrl { get; set; }
}

public class Film
{
    [JsonPropertyName("nom")]
    public string? Nom { get; set; }

    [JsonPropertyName("slug")]
    public string Slug { get; set; } = string.Empty;

    [JsonPropertyName("lang")]
    public string? Lang { get; set; }

    [JsonPropertyName("image")]
    public string? Image { get; set; }

    [JsonPropertyName("videos")]
    public List<VideoSource> Videos { get; set; } = new();
}

public class Scan
{
    [JsonPropertyName("nom")]
    public string Nom { get; set; } = string.Empty;

    [JsonPropertyName("slug")]
    public string Slug { get; set; } = string.Empty;

    [JsonPropertyName("lang")]
    public string? Lang { get; set; }

    [JsonPropertyName("chapitres")]
    public List<Chapitre> Chapitres { get; set; } = new();
}

public class Chapitre
{
    [JsonPropertyName("numero")]
    public double Numero { get; set; }

    [JsonPropertyName("titre")]
    public string? Titre { get; set; }

    [JsonPropertyName("images")]
    public List<string> Images { get; set; } = new();
}

// ── Recherche / Admin ────────────────────────────────────────────────────────

public class SiteSearchResult
{
    [JsonPropertyName("nom")]
    public string Nom { get; set; } = string.Empty;

    [JsonPropertyName("slug")]
    public string? Slug { get; set; }

    [JsonPropertyName("url")]
    public string? Url { get; set; }

    [JsonPropertyName("image")]
    public string? Image { get; set; }

    [JsonPropertyName("genres")]
    public List<string> Genres { get; set; } = new();
}

// ── Films & séries (source TMDB + Vidzy, indépendante d'anime-sama.to) ─────────

public class TmdbSearchResult
{
    [JsonPropertyName("tmdb_id")]
    public int TmdbId { get; set; }

    [JsonPropertyName("media_type")]
    public string MediaType { get; set; } = string.Empty; // "movie" | "tv"

    [JsonPropertyName("slug")]
    public string Slug { get; set; } = string.Empty;

    [JsonPropertyName("nom")]
    public string Nom { get; set; } = string.Empty;

    [JsonPropertyName("image")]
    public string? Image { get; set; }

    [JsonPropertyName("annee")]
    public int? Annee { get; set; }

    [JsonPropertyName("note")]
    public double? Note { get; set; }

    [JsonPropertyName("in_db")]
    public bool InDb { get; set; }
}

public class SyncStarted
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("slug")]
    public string Slug { get; set; } = string.Empty;
}

public class SyncStatusResponse
{
    [JsonPropertyName("slug")]
    public string Slug { get; set; } = string.Empty;

    // idle | syncing | done | error | never_synced
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("progress")]
    public int Progress { get; set; }

    [JsonPropertyName("message")]
    public string? Message { get; set; }
}

public class JobCreated
{
    [JsonPropertyName("job_id")]
    public string JobId { get; set; } = string.Empty;

    [JsonPropertyName("output_name")]
    public string OutputName { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;
}

public class JobStatus
{
    [JsonPropertyName("job_id")]
    public string JobId { get; set; } = string.Empty;

    // pending | downloading | ready | error
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("progress")]
    public int Progress { get; set; }

    [JsonPropertyName("error")]
    public string? Error { get; set; }

    [JsonPropertyName("ready")]
    public bool Ready { get; set; }
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

    [JsonPropertyName("headers")]
    public Dictionary<string, string> Headers { get; set; } = new();

    [JsonPropertyName("title")]
    public string? Title { get; set; }

    [JsonPropertyName("duration")]
    public int? Duration { get; set; }

    [JsonPropertyName("merged")]
    public bool Merged { get; set; }
}
