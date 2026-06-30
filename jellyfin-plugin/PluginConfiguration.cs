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
}
