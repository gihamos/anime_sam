import { useCallback, useEffect, useRef } from 'react';
import * as FileSystem from 'expo-file-system';
import { downloadApi, getToken } from '@/services/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useDownloadStore } from '@/stores/downloadStore';
import { ActiveJob, LocalFile } from '@/types';

const POLL_INTERVAL = 2000; // ms

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} Mo`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} Go`;
}

export function formatSpeed(bytesPerSec: number): string {
  return `${formatBytes(bytesPerSec)}/s`;
}

export function formatEta(seconds: number): string {
  if (seconds <= 0) return '';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

// Démarre un job de téléchargement épisode et l'ajoute au store
export function useStartEpisodeDownload() {
  const { addJob } = useDownloadStore();

  return useCallback(async (params: {
    slug: string;
    catalogueNom: string;
    saisonIdx: number;
    saisonNom?: string;
    nums?: number[];
  }) => {
    const created = await downloadApi.createEpisodeJob({
      slug:       params.slug,
      saison_idx: params.saisonIdx,
      nums:       params.nums,
    });

    const label = params.nums
      ? `${params.saisonNom ?? 'Saison'} · Ép. ${params.nums.join(', ')}`
      : (params.saisonNom ?? 'Saison entière');

    const job: ActiveJob = {
      job_id:        created.job_id,
      slug:          params.slug,
      catalogue_nom: params.catalogueNom,
      label,
      status:        'pending',
      progress:      0,
      dl_speed:      0,
      dl_eta:        0,
      output_name:   created.output_name,
      is_single:     created.is_single,
      nb_items:      created.nb_items,
      error:         '',
      created_at:    Date.now(),
    };

    addJob(job);
    return job;
  }, [addJob]);
}

export function useStartFilmDownload() {
  const { addJob } = useDownloadStore();

  return useCallback(async (params: {
    slug: string;
    catalogueNom: string;
    filmIdx: number;
    filmNom?: string;
  }) => {
    const created = await downloadApi.createFilmJob({
      slug:     params.slug,
      film_idx: params.filmIdx,
    });

    const job: ActiveJob = {
      job_id:        created.job_id,
      slug:          params.slug,
      catalogue_nom: params.catalogueNom,
      label:         params.filmNom ?? 'Film',
      status:        'pending',
      progress:      0,
      dl_speed:      0,
      dl_eta:        0,
      output_name:   created.output_name,
      is_single:     created.is_single,
      nb_items:      created.nb_items,
      error:         '',
      created_at:    Date.now(),
    };

    addJob(job);
    return job;
  }, [addJob]);
}

// Polling de tous les jobs actifs + téléchargement local quand ready
export function useJobPoller() {
  const { jobs, updateJob, removeJob, addLocalFile } = useDownloadStore();
  const { apiUrl } = useSettingsStore();
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const downloadingRef = useRef<Set<string>>(new Set());

  const saveLocalFile = useCallback(async (job: ActiveJob) => {
    if (downloadingRef.current.has(job.job_id)) return;
    downloadingRef.current.add(job.job_id);

    try {
      const token  = await getToken();
      const url    = downloadApi.getFileUrl(job.job_id, apiUrl, token);
      const ext    = job.is_single ? 'mp4' : 'zip';
      const destDir = FileSystem.documentDirectory + 'downloads/';
      const dest   = `${destDir}${job.output_name}.${ext}`;

      await FileSystem.makeDirectoryAsync(destDir, { intermediates: true });

      const dlRes = await FileSystem.downloadAsync(url, dest, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (dlRes.status === 200) {
        const info = await FileSystem.getInfoAsync(dlRes.uri, { size: true });
        const localFile: LocalFile = {
          id:            `${job.job_id}-${Date.now()}`,
          slug:          job.slug,
          catalogue_nom: job.catalogue_nom,
          label:         job.label,
          output_name:   job.output_name,
          local_uri:     dlRes.uri,
          is_single:     job.is_single,
          size_bytes:    (info as any).size ?? 0,
          downloaded_at: Date.now(),
        };
        addLocalFile(localFile);
        removeJob(job.job_id);
        // Nettoyage côté serveur
        downloadApi.cancel(job.job_id).catch(() => {});
      } else {
        updateJob(job.job_id, { status: 'error', error: `HTTP ${dlRes.status}` });
      }
    } catch (err: any) {
      updateJob(job.job_id, { status: 'error', error: err.message ?? 'Erreur inconnue' });
    } finally {
      downloadingRef.current.delete(job.job_id);
    }
  }, [apiUrl, addLocalFile, removeJob, updateJob]);

  const pollOnce = useCallback(async () => {
    const active = jobs.filter((j) => j.status === 'pending' || j.status === 'downloading');
    if (active.length === 0) return;

    await Promise.allSettled(
      active.map(async (job) => {
        try {
          const s = await downloadApi.getStatus(job.job_id);
          updateJob(job.job_id, {
            status:    s.status,
            progress:  s.progress,
            dl_speed:  s.dl_speed,
            dl_eta:    s.dl_eta,
            output_name: s.output_name || job.output_name,
            error:     s.error,
          });

          if (s.ready) {
            await saveLocalFile({ ...job, output_name: s.output_name || job.output_name });
          }
        } catch {
          // job peut avoir expiré côté serveur
        }
      })
    );
  }, [jobs, updateJob, saveLocalFile]);

  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === 'pending' || j.status === 'downloading');
    if (hasActive) {
      pollingRef.current = setInterval(pollOnce, POLL_INTERVAL);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [jobs, pollOnce]);
}

// Supprimer un fichier local (disque + store)
export async function deleteLocalFile(file: LocalFile, removeFromStore: (id: string) => void) {
  try {
    await FileSystem.deleteAsync(file.local_uri, { idempotent: true });
  } catch {}
  removeFromStore(file.id);
}
