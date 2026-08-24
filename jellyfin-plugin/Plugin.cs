using System;
using System.Collections.Generic;
using Jellyfin.Plugin.AnimeSama.Api;
using Jellyfin.Plugin.AnimeSama.Tasks;
using MediaBrowser.Common.Configuration;
using MediaBrowser.Common.Plugins;
using MediaBrowser.Model.Plugins;
using MediaBrowser.Model.Serialization;
using MediaBrowser.Model.Tasks;

namespace Jellyfin.Plugin.AnimeSama;

public class Plugin : BasePlugin<PluginConfiguration>, IHasWebPages
{
    public static Plugin? Instance { get; private set; }

    public Plugin(IApplicationPaths applicationPaths, IXmlSerializer xmlSerializer, ITaskManager taskManager)
        : base(applicationPaths, xmlSerializer)
    {
        Instance = this;
        ApiClient = new AnimeSamaClient(() => Configuration);
        AutoSyncScheduler.Start(taskManager);
    }

    // Renommé : le plugin couvre maintenant animés (anime-sama.to), films et séries
    // (TMDB + Vidzy) — pas juste les animés. Renommage d'affichage uniquement : Id (GUID),
    // AssemblyName et dossier d'installation inchangés, aucune réinstallation nécessaire.
    public override string Name => "Anime Sama Media";

    public override string Description => "Animés (anime-sama.to), films et séries (TMDB) directement dans Jellyfin. Développé par Taïse De Thèse Yabie — https://github.com/gihamos/";

    public override Guid Id => new("a4b1c2d3-e4f5-6789-abcd-ef0123456789");

    public AnimeSamaClient ApiClient { get; }

    public IEnumerable<PluginPageInfo> GetPages()
    {
        yield return new PluginPageInfo
        {
            Name = "AnimeSamaConfigPage",
            EmbeddedResourcePath = $"{GetType().Namespace}.Configuration.configPage.html",
        };
    }
}
