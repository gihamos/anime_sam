using System;
using System.Collections.Generic;
using Jellyfin.Plugin.AnimeSama.Api;
using MediaBrowser.Common.Configuration;
using MediaBrowser.Common.Plugins;
using MediaBrowser.Model.Plugins;
using MediaBrowser.Model.Serialization;

namespace Jellyfin.Plugin.AnimeSama;

public class Plugin : BasePlugin<PluginConfiguration>, IHasWebPages
{
    public static Plugin? Instance { get; private set; }

    public Plugin(IApplicationPaths applicationPaths, IXmlSerializer xmlSerializer)
        : base(applicationPaths, xmlSerializer)
    {
        Instance = this;
        ApiClient = new AnimeSamaClient(() => Configuration);
    }

    public override string Name => "Anime Sama";

    public override string Description => "Parcourez les animés de votre instance Anime Sama directement dans Jellyfin.";

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
