using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.AnimeSama.Api;
using MediaBrowser.Model.Tasks;

namespace Jellyfin.Plugin.AnimeSama.Tasks;

public class SyncLibraryTask : IScheduledTask
{
    private static readonly HttpClient ImageHttp = new() { Timeout = TimeSpan.FromSeconds(30) };

    public string Name        => "Synchroniser la bibliothèque Anime Sama";
    public string Key         => "AnimeSamaSyncLibrary";
    public string Description => "Crée ou met à jour les fichiers vidéo (.strm/.mp4) et mangas (.cbz) dans la bibliothèque Anime Sama.";
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
        var mangaLibPath = config.MangaLibraryPath?.TrimEnd('/') ?? string.Empty;
        var jellyfinBase = config.JellyfinPublicUrl?.TrimEnd('/') ?? string.Empty;
        var downloadMode = config.DownloadVideos;

        if (string.IsNullOrWhiteSpace(libPath))
            throw new InvalidOperationException("LibraryPath non configuré dans les paramètres du plugin.");
        if (!downloadMode && string.IsNullOrWhiteSpace(jellyfinBase))
            throw new InvalidOperationException("JellyfinPublicUrl non configuré dans les paramètres du plugin.");

        Directory.CreateDirectory(libPath);
        if (!string.IsNullOrWhiteSpace(mangaLibPath)) Directory.CreateDirectory(mangaLibPath);
        progress.Report(1);

        // ── 1. Récupérer tous les catalogues déjà synchronisés ───────────────────
        var all = await client.GetAllCataloguesAsync(ct).ConfigureAwait(false);
        var catalogues = all.Where(c => c.EpisodesSynced).ToList();
        if (catalogues.Count == 0) { progress.Report(100); return; }

        double step = 95.0 / catalogues.Count;
        int idx = 0;

        foreach (var summary in catalogues)
        {
            ct.ThrowIfCancellationRequested();
            progress.Report(2 + idx * step);
            idx++;

            bool isScan = string.Equals(summary.Type, "scan", StringComparison.OrdinalIgnoreCase);
            if (isScan && string.IsNullOrWhiteSpace(mangaLibPath)) continue;

            try
            {
                var detail = await client.GetCatalogueAsync(summary.Slug, ct).ConfigureAwait(false);
                if (detail is null) continue;

                if (isScan)
                    await SyncMangaAsync(detail, mangaLibPath, ct).ConfigureAwait(false);
                else
                    await SyncVideosAsync(client, detail, libPath, jellyfinBase, downloadMode, ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException) { throw; }
            catch { /* catalogue ignoré en cas d'erreur, on continue */ }
        }

        progress.Report(100);
    }

    // ── Vidéos (animes/films) ────────────────────────────────────────────────

    private static async Task SyncVideosAsync(
        AnimeSamaClient client, CatalogueDetail detail, string libPath,
        string jellyfinBase, bool downloadMode, CancellationToken ct)
    {
        var dirName = SanitizeName(detail.Titre);
        if (string.IsNullOrWhiteSpace(dirName)) dirName = detail.Slug;
        var seriesDir = Path.Combine(libPath, dirName);
        Directory.CreateDirectory(seriesDir);

        WriteTvShowNfo(seriesDir, detail);

        // Une entrée Saison = une langue ; on regroupe par nom pour créer un seul dossier Season N
        var saisonsByName = detail.Saisons.GroupBy(s => s.Nom).ToList();

        for (int sIdx = 0; sIdx < saisonsByName.Count; sIdx++)
        {
            var group     = saisonsByName[sIdx];
            var seasonDir = Path.Combine(seriesDir, $"Season {sIdx + 1}");
            Directory.CreateDirectory(seasonDir);

            foreach (var saison in group)
            {
                var langTag = saison.Lang.ToUpperInvariant();
                // Index brut nécessaire pour l'API de téléchargement (saison_idx)
                var rawSaisonIdx = detail.Saisons.IndexOf(saison);

                foreach (var ep in saison.Episodes)
                {
                    var urls = ep.Videos.Select(v => v.PlayerUrl).Where(u => !string.IsNullOrEmpty(u)).ToList();
                    if (urls.Count == 0) continue;

                    var epTitle  = SanitizeName(ep.Titre ?? $"Episode {ep.Numero}");
                    var baseName = $"S{sIdx + 1:D2}E{ep.Numero:D3} - {epTitle} [{langTag}]";

                    if (downloadMode)
                        await DownloadEpisodeAsync(client, seasonDir, baseName, detail.Slug, rawSaisonIdx, ep.Numero, ct).ConfigureAwait(false);
                    else
                        WriteStrm(seasonDir, baseName, jellyfinBase, urls!);
                }
            }
        }

        for (int fIdx = 0; fIdx < detail.Films.Count; fIdx++)
        {
            var film = detail.Films[fIdx];
            var urls = film.Videos.Select(v => v.PlayerUrl).Where(u => !string.IsNullOrEmpty(u)).ToList();
            if (urls.Count == 0) continue;

            var filmTitle = SanitizeName(film.Nom ?? $"Film {fIdx + 1}");
            var langTag   = film.Lang?.ToUpperInvariant() ?? "DEFAULT";
            var baseName  = $"{filmTitle} [{langTag}]";

            if (downloadMode)
                await DownloadFilmAsync(client, seriesDir, baseName, detail.Slug, fIdx, ct).ConfigureAwait(false);
            else
                WriteStrm(seriesDir, baseName, jellyfinBase, urls!);
        }
    }

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

    // ── Mangas / scans (.cbz) ────────────────────────────────────────────────

    private static async Task SyncMangaAsync(CatalogueDetail detail, string mangaLibPath, CancellationToken ct)
    {
        var dirName = SanitizeName(detail.Titre);
        if (string.IsNullOrWhiteSpace(dirName)) dirName = detail.Slug;
        var mangaDir = Path.Combine(mangaLibPath, dirName);
        Directory.CreateDirectory(mangaDir);

        // Couverture de la série (cover.jpg + folder.jpg — Jellyfin accepte les deux)
        if (!string.IsNullOrEmpty(detail.Image))
        {
            var coverPath = Path.Combine(mangaDir, "cover.jpg");
            if (!File.Exists(coverPath))
            {
                try
                {
                    var bytes = await ImageHttp.GetByteArrayAsync(detail.Image, ct).ConfigureAwait(false);
                    await File.WriteAllBytesAsync(coverPath, bytes, ct).ConfigureAwait(false);
                    // Alias folder.jpg pour maximiser la compatibilité
                    File.Copy(coverPath, Path.Combine(mangaDir, "folder.jpg"), overwrite: true);
                }
                catch { /* image indisponible — on continue sans couverture */ }
            }
        }

        foreach (var scan in detail.Scans)
        {
            foreach (var chapitre in scan.Chapitres)
            {
                ct.ThrowIfCancellationRequested();
                if (chapitre.Images.Count == 0) continue;

                var numStr   = chapitre.Numero % 1 == 0 ? $"{chapitre.Numero:000}" : chapitre.Numero.ToString("000.0#");
                var chapTitle = SanitizeName(chapitre.Titre ?? $"Chapitre {numStr}");
                var cbzPath  = Path.Combine(mangaDir, $"{dirName} - Chapitre {numStr} - {chapTitle}.cbz");

                if (File.Exists(cbzPath)) continue; // déjà téléchargé — sync idempotente

                if (await BuildCbzAsync(cbzPath, chapitre, detail, ct).ConfigureAwait(false))
                    continue;

                // Échec partiel/total — ne pas laisser un .cbz corrompu/vide
                if (File.Exists(cbzPath)) File.Delete(cbzPath);
            }
        }
    }

    private static async Task<bool> BuildCbzAsync(
        string cbzPath, Chapitre chapitre, CatalogueDetail detail, CancellationToken ct)
    {
        var tmpPath = cbzPath + ".tmp";
        try
        {
            int imagesWritten = 0;
            using (var fs  = File.Create(tmpPath))
            using (var zip = new ZipArchive(fs, ZipArchiveMode.Create))
            {
                for (int i = 0; i < chapitre.Images.Count; i++)
                {
                    ct.ThrowIfCancellationRequested();
                    byte[] bytes;
                    try
                    {
                        bytes = await ImageHttp.GetByteArrayAsync(chapitre.Images[i], ct).ConfigureAwait(false);
                    }
                    catch { continue; } // image manquante — on passe à la suivante

                    var ext   = GuessExtension(chapitre.Images[i]);
                    var entry = zip.CreateEntry($"{i + 1:D3}{ext}", CompressionLevel.NoCompression);
                    await using var es = entry.Open();
                    await es.WriteAsync(bytes, ct).ConfigureAwait(false);
                    imagesWritten++;
                }

                var info = zip.CreateEntry("ComicInfo.xml");
                await using var infoStream = info.Open();
                var xml = BuildComicInfoXml(detail, chapitre);
                var xmlBytes = Encoding.UTF8.GetBytes(xml);
                await infoStream.WriteAsync(xmlBytes, ct).ConfigureAwait(false);
            }

            if (imagesWritten == 0) { File.Delete(tmpPath); return false; }

            File.Move(tmpPath, cbzPath, overwrite: true);
            return true;
        }
        catch
        {
            if (File.Exists(tmpPath)) File.Delete(tmpPath);
            return false;
        }
    }

    private static string GuessExtension(string imageUrl)
    {
        var clean = imageUrl.Split('?', '#')[0];
        var ext   = Path.GetExtension(clean);
        return string.IsNullOrWhiteSpace(ext) || ext.Length > 5 ? ".jpg" : ext;
    }

    private static string BuildComicInfoXml(CatalogueDetail detail, Chapitre chapitre)
    {
        var sb = new StringBuilder();
        sb.AppendLine("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
        sb.AppendLine("<ComicInfo xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\">");
        sb.AppendLine($"  <Series>{Xe(detail.Titre)}</Series>");
        sb.AppendLine($"  <Title>{Xe(chapitre.Titre ?? $"Chapitre {chapitre.Numero}")}</Title>");
        sb.AppendLine($"  <Number>{chapitre.Numero}</Number>");
        if (!string.IsNullOrEmpty(detail.Synopsis))
            sb.AppendLine($"  <Summary>{Xe(detail.Synopsis)}</Summary>");
        foreach (var genre in detail.Genres)
            sb.AppendLine($"  <Genre>{Xe(genre)}</Genre>");
        sb.AppendLine("</ComicInfo>");
        return sb.ToString();
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
