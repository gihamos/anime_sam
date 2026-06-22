using MediaBrowser.Model.Plugins;

namespace Jellyfin.Plugin.AnimeSama;

public class PluginConfiguration : BasePluginConfiguration
{
    public string ApiUrl { get; set; } = "http://localhost:8000";
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;

    // Légèrement inférieur à JWT_EXPIRE_MINUTES pour forcer le refresh avant expiration
    public int TokenExpiryMinutes { get; set; } = 1420;
}
