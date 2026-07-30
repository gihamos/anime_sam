import { useCallback, useEffect, useRef } from 'react';
import * as FileSystem from 'expo-file-system/legacy';
import { downloadApi, scanDownloadApi, getToken } from '@/services/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useDownloadStore } from '@/stores/downloadStore';
import { notifyLocal } from '@/services/notifications';
import { ActiveJob, LocalFile, LocalScanChapter } from '@/types';

function notifyDownloadEvent(title: string, body: string): void {
  if (!useSettingsStore.getState().notifyDownloads) return;
  notifyLocal(title, body);
}

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

// ─── Démarrage jobs vidéo / film ──────────────────────────────────────────────

export function useStartEpisodeDownload() {
  const { addJob } = useDownloadStore();

  return useCallback(async (params: {
    slug: string;
    catalogueNom: string;
    saisonIdx: number;
    saisonNom?: string;
    nums?: number[];
  }) => {
    // Plusieurs épisodes : un job PAR épisode (mp4 individuel) plutôt qu'un
    // seul job zippé — chaque épisode reste lisible seul (interne ou externe)
    // dès qu'il termine, sans avoir à extraire une archive. Ils tournent en
    // parallèle côté serveur (limité par un sémaphore côté API).
    if (params.nums && params.nums.length > 1) {
      const jobs: ActiveJob[] = [];
      for (const num of params.nums) {
        const created = await downloadApi.createEpisodeJob({
          slug:       params.slug,
          saison_idx: params.saisonIdx,
          nums:       [num],
        });
        const job: ActiveJob = {
          job_id:        created.job_id,
          slug:          params.slug,
          catalogue_nom: params.catalogueNom,
          label:         `${params.saisonNom ?? 'Saison'} · Ép. ${num}`,
          status:        'pending',
          progress:      0,
          dl_speed:      0,
          dl_eta:        0,
          output_name:   created.output_name,
          is_single:     created.is_single,
          nb_items:      created.nb_items,
          error:         '',
          created_at:    Date.now(),
          job_type:      'video',
          saison_idx:    params.saisonIdx,
          ep_nums:       [num],
        };
        addJob(job);
        jobs.push(job);
      }
      return jobs;
    }

    const created = await downloadApi.createEpisodeJob({
      slug:       params.slug,
      saison_idx: params.saisonIdx,
      nums:       params.nums,
    });

    const label = params.nums
      ? `${params.saisonNom ?? 'Saison'} · Ép. ${params.nums.join(', ')}`
      : (params.saisonNom ?? 'Épisode');

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
      job_type:      'video',
      saison_idx:    params.saisonIdx,
      ep_nums:       params.nums,
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
      job_type:      'video',
      film_idx:      params.filmIdx,
    };

    addJob(job);
    return job;
  }, [addJob]);
}

// ─── Démarrage job scan ───────────────────────────────────────────────────────

export function useStartScanDownload() {
  const { addJob } = useDownloadStore();

  return useCallback(async (params: {
    slug: string;
    catalogueNom: string;
    scanSlug: string;
    scanNom: string;
    chapitreNums: number[];
    chapitreLabel?: string;
  }) => {
    const created = await scanDownloadApi.createJob({
      slug:          params.slug,
      scan_slug:     params.scanSlug,
      chapitre_nums: params.chapitreNums,
    });

    const label = params.chapitreLabel
      ?? (params.chapitreNums.length === 1
          ? `Ch. ${params.chapitreNums[0]}`
          : `Ch. ${params.chapitreNums[0]}–${params.chapitreNums[params.chapitreNums.length - 1]}`);

    const job: ActiveJob = {
      job_id:        created.job_id,
      slug:          params.slug,
      catalogue_nom: params.catalogueNom,
      label:         `${params.scanNom} · ${label}`,
      status:        'pending',
      progress:      0,
      dl_speed:      0,
      dl_eta:        0,
      output_name:   '',
      is_single:     false,
      nb_items:      created.total_pages,
      error:         '',
      created_at:    Date.now(),
      job_type:      'scan',
      scan_slug:     params.scanSlug,
      chapitre_nums: params.chapitreNums,
    };

    addJob(job);
    return { job, created };
  }, [addJob]);
}

// ─── Téléchargement local des pages d'un job scan prêt ───────────────────────

async function saveScanChapters(
  job: ActiveJob,
  apiUrl: string,
  addScanChapter: (ch: LocalScanChapter) => void,
  removeJob: (id: string) => void,
  updateJob: (id: string, patch: Partial<ActiveJob>) => void,
): Promise<void> {
  try {
    const token    = await getToken();
    const manifest = await scanDownloadApi.getManifest(job.job_id);

    for (const ch of manifest.chapters) {
      if (ch.page_count === 0) continue;

      const destDir = `${FileSystem.documentDirectory}scans/${job.slug}/${job.scan_slug ?? manifest.scan_slug}/ch_${ch.num}/`;
      await FileSystem.makeDirectoryAsync(destDir, { intermediates: true });

      // Télécharger les pages en parallèle (max 4 simultanés)
      const localPages: string[] = new Array(ch.page_count).fill('');
      const queue = Array.from({ length: ch.page_count }, (_, i) => i);
      const concurrency = 4;

      async function worker(): Promise<void> {
        while (queue.length > 0) {
          const idx = queue.shift();
          if (idx === undefined) return;
          const url  = scanDownloadApi.getPageUrl(job.job_id, ch.num, idx, apiUrl, token);
          const dest = `${destDir}page_${String(idx).padStart(4, '0')}.jpg`;
          try {
            const res = await FileSystem.downloadAsync(url, dest, {
              headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            if (res.status === 200) {
              localPages[idx] = res.uri;
            }
          } catch {}
        }
      }

      await Promise.all(Array.from({ length: concurrency }, () => worker()));

      const downloaded = localPages.filter(Boolean);
      if (downloaded.length === 0) continue;

      let sizeBytes = 0;
      for (const uri of downloaded) {
        try {
          const info = await FileSystem.getInfoAsync(uri);
          sizeBytes += (info as any).size ?? 0;
        } catch {}
      }

      const localChapter: LocalScanChapter = {
        id:             `${job.slug}_${job.scan_slug ?? manifest.scan_slug}_${ch.num}`,
        slug:           job.slug,
        catalogue_nom:  job.catalogue_nom,
        scan_slug:      job.scan_slug ?? manifest.scan_slug,
        scan_nom:       job.label.split(' · ')[0] ?? '',
        chapitre_num:   ch.num,
        chapitre_titre: ch.titre,
        local_pages:    localPages,
        page_count:     downloaded.length,
        size_bytes:     sizeBytes,
        downloaded_at:  Date.now(),
      };
      addScanChapter(localChapter);
    }

    removeJob(job.job_id);
    scanDownloadApi.cancel(job.job_id).catch(() => {});
    notifyDownloadEvent('Téléchargement terminé', job.label);
  } catch (err: any) {
    updateJob(job.job_id, { status: 'error', error: err?.message ?? 'Erreur inconnue' });
    notifyDownloadEvent('Échec du téléchargement', job.label);
  }
}

// ─── Poller unifié (vidéo + scan) ─────────────────────────────────────────────

export function useJobPoller() {
  const { jobs, updateJob, removeJob, addLocalFile, addScanChapter } = useDownloadStore();
  const { apiUrl } = useSettingsStore();
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const processingRef = useRef<Set<string>>(new Set());

  // ── Sauvegarde fichier vidéo local ───────────────────────────────────────────
  const saveLocalFile = useCallback(async (job: ActiveJob) => {
    if (processingRef.current.has(job.job_id)) return;
    processingRef.current.add(job.job_id);

    try {
      const token   = await getToken();
      const url     = downloadApi.getFileUrl(job.job_id, apiUrl, token);
      const ext     = job.is_single ? 'mp4' : 'zip';
      const destDir = FileSystem.documentDirectory + 'downloads/';
      const dest    = `${destDir}${job.output_name}.${ext}`;

      await FileSystem.makeDirectoryAsync(destDir, { intermediates: true });

      const dlRes = await FileSystem.downloadAsync(url, dest, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (dlRes.status === 200) {
        const info = await FileSystem.getInfoAsync(dlRes.uri);
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
        downloadApi.cancel(job.job_id).catch(() => {});
        notifyDownloadEvent('Téléchargement terminé', job.label);
      } else {
        updateJob(job.job_id, { status: 'error', error: `HTTP ${dlRes.status}` });
        notifyDownloadEvent('Échec du téléchargement', job.label);
      }
    } catch (err: any) {
      updateJob(job.job_id, { status: 'error', error: err.message ?? 'Erreur inconnue' });
      notifyDownloadEvent('Échec du téléchargement', job.label);
    } finally {
      processingRef.current.delete(job.job_id);
    }
  }, [apiUrl, addLocalFile, removeJob, updateJob]);

  // ── Sauvegarde chapitre scan local ───────────────────────────────────────────
  const saveScanJob = useCallback(async (job: ActiveJob) => {
    if (processingRef.current.has(job.job_id)) return;
    processingRef.current.add(job.job_id);
    try {
      await saveScanChapters(job, apiUrl, addScanChapter, removeJob, updateJob);
    } finally {
      processingRef.current.delete(job.job_id);
    }
  }, [apiUrl, addScanChapter, removeJob, updateJob]);

  // ── Polling ───────────────────────────────────────────────────────────────────
  const pollOnce = useCallback(async () => {
    const active = jobs.filter((j) => j.status === 'pending' || j.status === 'downloading');
    if (active.length === 0) return;

    await Promise.allSettled(
      active.map(async (job) => {
        try {
          if (job.job_type === 'scan') {
            const s = await scanDownloadApi.getStatus(job.job_id);
            updateJob(job.job_id, {
              status:   s.status,
              progress: s.progress,
              nb_items: s.total_pages,
              error:    s.error,
            });
            if (s.ready) {
              await saveScanJob(job);
            } else if (s.status === 'error') {
              notifyDownloadEvent('Échec du téléchargement', job.label);
            }
          } else {
            const s = await downloadApi.getStatus(job.job_id);
            updateJob(job.job_id, {
              status:      s.status,
              progress:    s.progress,
              dl_speed:    s.dl_speed,
              dl_eta:      s.dl_eta,
              output_name: s.output_name || job.output_name,
              error:       s.error,
            });
            if (s.ready) {
              await saveLocalFile({ ...job, output_name: s.output_name || job.output_name });
            } else if (s.status === 'error') {
              notifyDownloadEvent('Échec du téléchargement', job.label);
            }
          }
        } catch {
          // job peut avoir expiré côté serveur
        }
      })
    );
  }, [jobs, updateJob, saveLocalFile, saveScanJob]);

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

// ─── Suppression fichier local (disque + store) ───────────────────────────────

export async function deleteLocalFile(file: LocalFile, removeFromStore: (id: string) => void) {
  try {
    await FileSystem.deleteAsync(file.local_uri, { idempotent: true });
  } catch {}
  removeFromStore(file.id);
}

export async function deleteLocalScanChapter(
  chapter: LocalScanChapter,
  removeFromStore: (id: string) => void,
) {
  const dir = `${FileSystem.documentDirectory}scans/${chapter.slug}/${chapter.scan_slug}/ch_${chapter.chapitre_num}/`;
  try {
    await FileSystem.deleteAsync(dir, { idempotent: true });
  } catch {}
  removeFromStore(chapter.id);
}
