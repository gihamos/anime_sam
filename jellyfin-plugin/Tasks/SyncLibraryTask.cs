using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.AnimeSama.Api;
using MediaBrowser.Model.Tasks;

namespace Jellyfin.Plugin.AnimeSama.Tasks;

public class SyncLibraryTask : IScheduledTask
{
    public string Name        => "Synchroniser la bibliothèque Anime Sama";
    public string Key         => "AnimeSamaSyncLibrary";
    public string Description => "Crée ou met à jour les fichiers .strm/.nfo (ou télécharge les vidéos) dans la bibliothèque Anime Sama.";
    public string Category    => "Anime Sama";

    public IEnumerable<TaskTriggerInfo> GetDefaultTriggers()
    {
        yield return new TaskTriggerInfo
        {
            Type = TaskTriggerInfo.TriggerDaily,
            TimeOfDayTicks = TimeSpan.FromHours(3).Ticks,
        };
    }

    public async Task ExecuteAsync(IProgress<double> progress, CancellationToken ct)
    {
        var plugin = Plugin.Instance
            ?? throw new InvalidOperationException("Plugin non initialisé.");

        var config       = plugin.Configuration;
        var client       = plugin.ApiClient;
        var libPath      = config.LibraryPath?.TrimEnd('/') ?? string.Empty;
        var jellyfinBase = config.JellyfinPublicUrl?.TrimEnd('/') ?? string.Empty;
        var downloadMode = config.DownloadVideos;

        if (string.IsNullOrWhiteSpace(libPath))
            throw new InvalidOperationException("LibraryPath non configuré dans les paramètres du plugin.");
        if (!downloadMode && string.IsNullOrWhiteSpace(jellyfinBase))
            throw new InvalidOperationException("JellyfinPublicUrl non configuré dans les paramètres du plugin.");

        Directory.CreateDirectory(libPath);
        progress.Report(1);

        // ── 1. Récupérer tous les catalogues, ne garder que ceux déjà synchronisés ──
        var all = await client.GetAllCataloguesAsync(ct).ConfigureAwait(false);
        var catalogues = all
            .Where(c => c.EpisodesSynced && !string.Equals(c.Type, "scan", StringComparison.OrdinalIgnoreCase))
            .ToList();

        if (catalogues.Count == 0) { progress.Report(100); return; }

        double step = 95.0 / catalogues.Count;
        int idx = 0;

        foreach (var summary in catalogues)
        {
            ct.ThrowIfCancellationRequested();
            progress.Report(2 + idx * step);
            idx++;

            try
            {
                var detail = await client.GetCatalogueAsync(summary.Slug, ct).ConfigureAwait(false);
                if (detail is null) continue;

                var dirName = SanitizeName(detail.Titre);
                if (string.IsNullOrWhiteSpace(dirName)) dirName = detail.Slug;
                var seriesDir = Path.Combine(libPath, dirName);
                Directory.CreateDirectory(seriesDir);

                WriteTvShowNfo(seriesDir, detail);

                // ── 2. Saisons (une entrée Saison = une langue, on regroupe par nom) ──
                var saisonsByName = detail.Saisons.GroupBy(s => s.Nom).ToList();

                for (int sIdx = 0; sIdx < saisonsByName.Count; sIdx++)
                {
                    var group     = saisonsByName[sIdx];
                    var seasonDir = Path.Combine(seriesDir, $"Season {sIdx + 1}");
                    Directory.CreateDirectory(seasonDir);

                    foreach (var saison in group)
                    {
                        var langTag = saison.Lang.ToUpperInvariant();
                        // Index de la saison "langue" dans la liste originale — nécessaire
                        // pour appeler l'API de téléchargement (saison_idx attend l'index brut)
                        var rawSaisonIdx = detail.Saisons.IndexOf(saison);

                        foreach (var ep in saison.Episodes)
                        {
                            var urls = ep.Videos.Select(v => v.PlayerUrl).Where(u => !string.IsNullOrEmpty(u)).ToList();
                            if (urls.Count == 0) continue;

                            var epTitle  = SanitizeName(ep.Titre ?? $"Episode {ep.Numero}");
                            var baseName = $"S{sIdx + 1:D2}E{ep.Numero:D3} - {epTitle} [{langTag}]";

                            if (downloadMode)
                            {
                                await DownloadEpisodeAsync(
                                    client, seasonDir, baseName, detail.Slug, rawSaisonIdx, ep.Numero, ct
                                ).ConfigureAwait(false);
                            }
                            else
                            {
                                WriteStrm(seasonDir, baseName, jellyfinBase, urls!);
                            }
                        }
                    }
                }

                // ── 3. Films ─────────────────────────────────────────────────
                for (int fIdx = 0; fIdx < detail.Films.Count; fIdx++)
                {
                    var film = detail.Films[fIdx];
                    var urls = film.Videos.Select(v => v.PlayerUrl).Where(u => !string.IsNullOrEmpty(u)).ToList();
                    if (urls.Count == 0) continue;

                    var filmTitle = SanitizeName(film.Nom ?? $"Film {fIdx + 1}");
                    var langTag   = film.Lang?.ToUpperInvariant() ?? "DEFAULT";
                    var baseName  = $"{filmTitle} [{langTag}]";

                    if (downloadMode)
                    {
                        await DownloadFilmAsync(client, seriesDir, baseName, detail.Slug, fIdx, ct).ConfigureAwait(false);
                    }
                    else
                    {
                        WriteStrm(seriesDir, baseName, jellyfinBase, urls!);
                    }
                }
            }
            catch (OperationCanceledException) { throw; }
            catch { /* catalogue ignoré en cas d'erreur, on continue */ }
        }

        progress.Report(100);
    }

    // ── Streaming (.strm) ────────────────────────────────────────────────────

    private static void WriteStrm(string dir, string baseName, string jellyfinBase, List<string> urls)
    {
        var strmPath = Path.Combine(dir, $"{baseName}.strm");
        if (File.Exists(strmPath)) return;

        // Une entrée 'url=' par lecteur candidat — le contrôleur essaie chacune
        // dans l'ordre et bascule sur la suivante si la résolution échoue.
        var query = string.Join("&", urls.Select(u => $"url={Uri.EscapeDataString(u)}"));
        var streamUrl = $"{jellyfinBase}/AnimeSama/stream?{query}";
        File.WriteAllText(strmPath, streamUrl, Encoding.UTF8);
    }

    // ── Téléchargement réel ──────────────────────────────────────────────────

    private static async Task DownloadEpisodeAsync(
        AnimeSamaClient client, string seasonDir, string baseName,
        string slug, int saisonIdx, int episodeNum, CancellationToken ct)
    {
        var destPath = Path.Combine(seasonDir, $"{baseName}.mp4");
        if (File.Exists(destPath)) return; // déjà téléchargé — sync idempotente

        var job = await client.CreateEpisodeDownloadJobAsync(slug, saisonIdx, episodeNum, ct).ConfigureAwait(false);
        if (job is null) return;

        await client.DownloadJobToFileAsync(job.JobId, destPath, ct).ConfigureAwait(false);
    }

    private static async Task DownloadFilmAsync(
        AnimeSamaClient client, string seriesDir, string baseName,
        string slug, int filmIdx, CancellationToken ct)
    {
        var destPath = Path.Combine(seriesDir, $"{baseName}.mp4");
        if (File.Exists(destPath)) return;

        var job = await client.CreateFilmDownloadJobAsync(slug, filmIdx, ct).ConfigureAwait(false);
        if (job is null) return;

        await client.DownloadJobToFileAsync(job.JobId, destPath, ct).ConfigureAwait(false);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static void WriteTvShowNfo(string dir, CatalogueDetail detail)
    {
        var sb = new StringBuilder();
        sb.AppendLine("<?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"yes\"?>");
        sb.AppendLine("<tvshow>");
        sb.AppendLine($"  <title>{Xe(detail.Titre)}</title>");
        if (!string.IsNullOrEmpty(detail.Synopsis))
            sb.AppendLine($"  <plot>{Xe(detail.Synopsis)}</plot>");
        if (!string.IsNullOrEmpty(detail.Image))
            sb.AppendLine($"  <thumb aspect=\"poster\">{Xe(detail.Image)}</thumb>");
        if (detail.Annee.HasValue)
            sb.AppendLine($"  <year>{detail.Annee}</year>");
        if (!string.IsNullOrEmpty(detail.Statut))
            sb.AppendLine($"  <status>{Xe(detail.Statut)}</status>");
        foreach (var genre in detail.Genres)
            sb.AppendLine($"  <genre>{Xe(genre)}</genre>");
        sb.AppendLine("</tvshow>");

        File.WriteAllText(Path.Combine(dir, "tvshow.nfo"), sb.ToString(), Encoding.UTF8);
    }

    private static string SanitizeName(string name)
    {
        var invalid = Path.GetInvalidFileNameChars();
        return string.Concat(name.Select(c => invalid.Contains(c) ? '_' : c)).Trim();
    }

    private static string Xe(string? s) =>
        (s ?? string.Empty)
            .Replace("&",  "&amp;")
            .Replace("<",  "&lt;")
            .Replace(">",  "&gt;")
            .Replace("\"", "&quot;");
}
