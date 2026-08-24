using System;
using System.Globalization;
using System.Threading;
using MediaBrowser.Model.Tasks;

namespace Jellyfin.Plugin.AnimeSama.Tasks;

/// <summary>
/// Planificateur "maison" pour la synchronisation automatique.
///
/// Pourquoi ne pas utiliser IScheduledTask.GetDefaultTriggers (le mécanisme natif
/// Jellyfin) ? Il ne connaît que Daily/Weekly/Interval — pas de "jour N du mois", qui est
/// pourtant l'une des fréquences demandées. On gère donc nous-mêmes tout le planning
/// (jour + heure, journalier/hebdomadaire/mensuel) à partir de la configuration du plugin,
/// via un simple minuteur qui vérifie périodiquement si l'échéance est atteinte.
///
/// Totalement indépendant du bouton "Synchroniser maintenant" (qui appelle directement
/// la tâche Jellyfin et s'exécute donc immédiatement, sans passer par ici).
/// </summary>
public static class AutoSyncScheduler
{
    private static Timer? _timer;
    private static ITaskManager? _taskManager;
    private static readonly TimeSpan CheckInterval = TimeSpan.FromMinutes(5);
    private static int _running; // 0/1 — évite un chevauchement si un cycle dépasse 5 min

    public static void Start(ITaskManager taskManager)
    {
        _taskManager = taskManager;
        if (_timer is not null) return; // déjà démarré (Plugin est un singleton)
        _timer = new Timer(_ => Tick(), null, CheckInterval, CheckInterval);
    }

    private static void Tick()
    {
        if (Interlocked.Exchange(ref _running, 1) == 1) return;
        try
        {
            var plugin = Plugin.Instance;
            if (plugin is null || _taskManager is null) return;
            var config = plugin.Configuration;
            if (!config.AutoSyncEnabled) return;

            var now = DateTime.Now;
            bool dueToday = config.AutoSyncFrequency switch
            {
                "Weekly"  => (int)now.DayOfWeek == config.AutoSyncDayOfWeek,
                "Monthly" => now.Day == Math.Clamp(config.AutoSyncDayOfMonth, 1, 28),
                _         => true, // "Daily"
            };
            if (!dueToday) return;

            var scheduledToday = new DateTime(now.Year, now.Month, now.Day, config.AutoSyncHour, config.AutoSyncMinute, 0);
            if (now < scheduledToday) return; // pas encore l'heure configurée

            if (DateTime.TryParse(
                    config.LastAutoSyncUtc, CultureInfo.InvariantCulture,
                    DateTimeStyles.RoundtripKind, out var lastUtc)
                && lastUtc.ToLocalTime() >= scheduledToday)
            {
                return; // déjà exécutée pour cette échéance
            }

            config.LastAutoSyncUtc = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture);
            plugin.SaveConfiguration();

            // Passe par le TaskManager Jellyfin (comme le bouton "Synchroniser maintenant")
            // plutôt que d'appeler SyncLibraryTask directement : visible dans Tableau de
            // bord → Tâches planifiées, journalisé nativement, et protégé contre un double
            // déclenchement si un admin lance une synchro manuelle au même moment.
            _taskManager.Execute<SyncLibraryTask>();
        }
        catch
        {
            // Ne doit jamais interrompre le minuteur — nouvelle tentative au prochain tick
            // (5 min plus tard), ou à la prochaine échéance si celle-ci est passée.
        }
        finally
        {
            Interlocked.Exchange(ref _running, 0);
        }
    }
}
