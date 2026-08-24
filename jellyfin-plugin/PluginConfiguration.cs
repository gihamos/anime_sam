using MediaBrowser.Model.Plugins;

namespace Jellyfin.Plugin.AnimeSama;

public class PluginConfiguration : BasePluginConfiguration
{
    public string ApiUrl { get; set; } = "http://localhost:8000";
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public int TokenExpiryMinutes { get; set; } = 1420;

    // Chemin sur le filesystem Jellyfin où les .strm seront créés
    public string LibraryPath { get; set; } = "/config/data/anime-sama";

    // URL publique de Jellyfin (ex: https://jellyfin.mondomaine.fr) — utilisée dans les .strm
    public string JellyfinPublicUrl { get; set; } = string.Empty;

    // Si activé : télécharge les fichiers vidéo réels (.mp4) au lieu de créer des .strm.
    // Plus lent et plus lourd sur disque, mais lecture locale fiable (pas de dépendance
    // au lecteur embed au moment du play). Idempotent — les fichiers déjà présents sont ignorés.
    public bool DownloadVideos { get; set; } = false;

    // Chemin où les mangas/scans seront créés en .cbz (un fichier par chapitre).
    // Pointez une bibliothèque Jellyfin de type "Livres" vers ce dossier.
    public string MangaLibraryPath { get; set; } = "/config/data/anime-sama-manga";

    // ── Films & séries (source TMDB + Vidzy — distincte des animés anime-sama.to) ──
    // Séparés de LibraryPath : structure de dossiers différente (film = un dossier plat par
    // titre, pas de Season N/) et pour que l'admin puisse pointer des bibliothèques Jellyfin
    // de type "Films"/"Séries" distinctes de la bibliothèque "Animés" existante.
    public string FilmLibraryPath  { get; set; } = "/config/data/films";
    public string SerieLibraryPath { get; set; } = "/config/data/series";

    // ── Planification automatique ────────────────────────────────────────────
    // Le déclencheur natif Jellyfin (IScheduledTask.GetDefaultTriggers) ne permet pas de
    // choisir "le jour N du mois" — le planning est donc entièrement géré par
    // Tasks/AutoSyncScheduler.cs à partir des champs ci-dessous, indépendamment du bouton
    // "Synchroniser maintenant" (qui lance toujours la tâche immédiatement).
    public bool AutoSyncEnabled { get; set; } = false;

    // "Daily" | "Weekly" | "Monthly"
    public string AutoSyncFrequency { get; set; } = "Daily";

    // 0 (dimanche) à 6 (samedi) — utilisé si AutoSyncFrequency == "Weekly"
    public int AutoSyncDayOfWeek { get; set; } = 1;

    // 1 à 28 — utilisé si AutoSyncFrequency == "Monthly" (plafonné à 28 pour rester valide
    // tous les mois, y compris février)
    public int AutoSyncDayOfMonth { get; set; } = 1;

    public int AutoSyncHour { get; set; } = 3;
    public int AutoSyncMinute { get; set; } = 0;

    // Horodatage UTC (ISO 8601) de la dernière exécution automatique — évite un second
    // déclenchement dans la même fenêtre si le serveur redémarre après l'heure planifiée.
    public string? LastAutoSyncUtc { get; set; }
}
