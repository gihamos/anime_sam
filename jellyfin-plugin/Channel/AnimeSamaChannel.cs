using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.AnimeSama.Api;
using MediaBrowser.Controller.Channels;
using MediaBrowser.Model.Channels;
using MediaBrowser.Model.Drawing;
using MediaBrowser.Model.Dto;
using MediaBrowser.Model.Entities;
using MediaBrowser.Model.MediaInfo;

namespace Jellyfin.Plugin.AnimeSama.Channel;

public class AnimeSamaChannel : IChannel, IRequiresMediaInfoCallback
{
    // ── IChannel — identité ───────────────────────────────────────────────────

    public string Name => "Anime Sama";

    public string Description => "Catalogue animés via votre instance Anime Sama.";

    public string DataVersion => "1";

    public string HomePageUrl => Plugin.Instance?.Configuration.ApiUrl ?? string.Empty;

    public ChannelParentalRating ParentalRating => ChannelParentalRating.GeneralAudience;

    public InternalChannelFeatures GetChannelFeatures() => new()
    {
        MediaTypes = new List<ChannelMediaType> { ChannelMediaType.Video },
        ContentTypes = new List<ChannelMediaContentType>
        {
            ChannelMediaContentType.Episode,
            ChannelMediaContentType.Movie,
        },
        MaxPageSize = 500,
        SupportsLatestMedia = false,
        CanFilter = false,
        CanSearch = false,
    };

    public bool IsEnabledFor(string userId) => true;

    public Task<DynamicImageResponse> GetChannelImage(ImageType type, CancellationToken cancellationToken)
        => Task.FromResult(new DynamicImageResponse { HasImage = false });

    public IEnumerable<ImageType> GetSupportedChannelImages()
        => Array.Empty<ImageType>();

    // ── Navigation ────────────────────────────────────────────────────────────

    public async Task<ChannelItemResult> GetChannelItems(
        InternalChannelItemQuery query,
        CancellationToken cancellationToken)
    {
        var client = GetClient();
        var folderId = query.FolderId;

        if (string.IsNullOrEmpty(folderId))
            return await GetRootAsync(client, cancellationToken).ConfigureAwait(false);

        var parts = folderId.Split(':');
        return parts[0] switch
        {
            "cat"    when parts.Length >= 2 => await GetCatalogueAsync(client, parts[1], cancellationToken).ConfigureAwait(false),
            "season" when parts.Length >= 3 => await GetSeasonAsync(client, parts[1], int.Parse(parts[2]), cancellationToken).ConfigureAwait(false),
            _                               => new ChannelItemResult { Items = Array.Empty<ChannelItemInfo>() },
        };
    }

    // Racine : liste de tous les catalogues
    private static async Task<ChannelItemResult> GetRootAsync(AnimeSamaClient client, CancellationToken ct)
    {
        var catalogues = await client.GetCataloguesAsync(ct).ConfigureAwait(false);

        var items = catalogues.Select(c => new ChannelItemInfo
        {
            Id       = $"cat:{c.Slug}",
            Name     = c.Titre,
            Overview = c.Synopsis,
            ImageUrl = c.Image,
            Type     = ChannelItemType.Folder,
        }).ToList();

        return new ChannelItemResult { Items = items, TotalRecordCount = items.Count };
    }

    // Catalogue : saisons + films
    private static async Task<ChannelItemResult> GetCatalogueAsync(AnimeSamaClient client, string slug, CancellationToken ct)
    {
        var cat = await client.GetCatalogueAsync(slug, ct).ConfigureAwait(false);
        if (cat is null)
            return new ChannelItemResult { Items = Array.Empty<ChannelItemInfo>() };

        var items = new List<ChannelItemInfo>();

        for (int i = 0; i < cat.Saisons.Count; i++)
        {
            var s = cat.Saisons[i];
            items.Add(new ChannelItemInfo
            {
                Id             = $"season:{slug}:{i}",
                Name           = s.Nom,
                ImageUrl       = cat.Image,
                Type           = ChannelItemType.Folder,
                ParentIndexNumber = i + 1,
            });
        }

        for (int i = 0; i < cat.Films.Count; i++)
        {
            var f = cat.Films[i];
            items.Add(new ChannelItemInfo
            {
                Id          = $"film:{slug}:{i}",
                Name        = f.Titre ?? $"Film {i + 1}",
                ImageUrl    = f.Image ?? cat.Image,
                Type        = ChannelItemType.Media,
                MediaType   = ChannelMediaType.Video,
                ContentType = ChannelMediaContentType.Movie,
            });
        }

        return new ChannelItemResult { Items = items, TotalRecordCount = items.Count };
    }

    // Saison : liste des épisodes (on prend la première langue disponible pour construire la liste)
    private static async Task<ChannelItemResult> GetSeasonAsync(AnimeSamaClient client, string slug, int saisonIdx, CancellationToken ct)
    {
        var cat = await client.GetCatalogueAsync(slug, ct).ConfigureAwait(false);
        if (cat is null || saisonIdx >= cat.Saisons.Count)
            return new ChannelItemResult { Items = Array.Empty<ChannelItemInfo>() };

        var saison = cat.Saisons[saisonIdx];

        // On se base sur la première langue pour obtenir la liste des numéros d'épisodes
        var refLang = saison.LanguesDisponibles.FirstOrDefault()
                   ?? saison.Episodes.Keys.FirstOrDefault();

        if (refLang is null || !saison.Episodes.TryGetValue(refLang, out var refEpisodes))
            return new ChannelItemResult { Items = Array.Empty<ChannelItemInfo>() };

        var items = refEpisodes.Select(ep => new ChannelItemInfo
        {
            Id                = $"ep:{slug}:{saisonIdx}:{ep.Num}",
            Name              = ep.Titre ?? $"Épisode {ep.Num}",
            Type              = ChannelItemType.Media,
            MediaType         = ChannelMediaType.Video,
            ContentType       = ChannelMediaContentType.Episode,
            ImageUrl          = cat.Image,
            IndexNumber       = ep.Num,
            ParentIndexNumber = saisonIdx + 1,
        }).ToList();

        return new ChannelItemResult { Items = items, TotalRecordCount = items.Count };
    }

    // ── Lecture — résolution des sources de stream ────────────────────────────

    public async Task<IEnumerable<MediaSourceInfo>> GetChannelItemMediaInfo(
        string id,
        CancellationToken cancellationToken)
    {
        var client = GetClient();
        var parts  = id.Split(':');

        if (parts[0] == "ep" && parts.Length >= 4)
            return await ResolveEpisodeAsync(client, parts[1], int.Parse(parts[2]), int.Parse(parts[3]), cancellationToken).ConfigureAwait(false);

        if (parts[0] == "film" && parts.Length >= 3)
            return await ResolveFilmAsync(client, parts[1], int.Parse(parts[2]), cancellationToken).ConfigureAwait(false);

        return Enumerable.Empty<MediaSourceInfo>();
    }

    // Épisode : résout toutes les langues disponibles en parallèle
    private static async Task<IEnumerable<MediaSourceInfo>> ResolveEpisodeAsync(
        AnimeSamaClient client, string slug, int saisonIdx, int epNum, CancellationToken ct)
    {
        var cat = await client.GetCatalogueAsync(slug, ct).ConfigureAwait(false);
        if (cat is null || saisonIdx >= cat.Saisons.Count)
            return Enumerable.Empty<MediaSourceInfo>();

        var saison = cat.Saisons[saisonIdx];

        var tasks = saison.LanguesDisponibles
            .Where(lang => saison.Episodes.ContainsKey(lang))
            .Select(async lang =>
            {
                var ep = saison.Episodes[lang].FirstOrDefault(e => e.Num == epNum);
                if (ep?.PlayerUrl is null) return (lang, (StreamResolveResponse?)null);
                try
                {
                    var stream = await client.ResolveStreamAsync(ep.PlayerUrl, ct).ConfigureAwait(false);
                    return (lang, stream);
                }
                catch
                {
                    return (lang, (StreamResolveResponse?)null);
                }
            });

        var results = await Task.WhenAll(tasks).ConfigureAwait(false);

        return results
            .Where(r => r.Item2?.Url is not null)
            .Select(r => BuildSource(r.Item2!, r.Item1.ToUpperInvariant()));
    }

    // Film
    private static async Task<IEnumerable<MediaSourceInfo>> ResolveFilmAsync(
        AnimeSamaClient client, string slug, int filmIdx, CancellationToken ct)
    {
        var cat = await client.GetCatalogueAsync(slug, ct).ConfigureAwait(false);
        if (cat is null || filmIdx >= cat.Films.Count)
            return Enumerable.Empty<MediaSourceInfo>();

        var film = cat.Films[filmIdx];
        if (film.PlayerUrl is null) return Enumerable.Empty<MediaSourceInfo>();

        try
        {
            var stream = await client.ResolveStreamAsync(film.PlayerUrl, ct).ConfigureAwait(false);
            if (stream?.Url is null) return Enumerable.Empty<MediaSourceInfo>();
            return new[] { BuildSource(stream, film.Lang?.ToUpperInvariant() ?? "Default") };
        }
        catch
        {
            return Enumerable.Empty<MediaSourceInfo>();
        }
    }

    // Construit un MediaSourceInfo à partir de la réponse du resolver
    private static MediaSourceInfo BuildSource(StreamResolveResponse stream, string label)
    {
        var proto = stream.Protocol?.ToLowerInvariant() switch
        {
            "m3u8" or "m3u8_native" or "http_dash_segments" => MediaProtocol.Http,
            _ => MediaProtocol.Http,
        };

        return new MediaSourceInfo
        {
            Id                   = label,
            Name                 = label,
            Protocol             = proto,
            Path                 = stream.Url!,
            Type                 = MediaSourceType.Default,
            IsRemote             = true,
            IsInfiniteStream     = false,
            Container            = stream.Ext ?? "mp4",
            RunTimeTicks         = stream.Duration.HasValue
                                   ? TimeSpan.FromSeconds(stream.Duration.Value).Ticks
                                   : (long?)null,
            RequiredHttpHeaders  = stream.Headers ?? new Dictionary<string, string>(),
        };
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static AnimeSamaClient GetClient()
        => Plugin.Instance?.ApiClient
           ?? throw new InvalidOperationException("Plugin Anime Sama non initialisé.");
}
