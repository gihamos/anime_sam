import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import * as FileSystem from 'expo-file-system';
import { ActiveJob, LocalFile, LocalScanChapter } from '@/types';

const JOBS_KEY  = 'anime_active_jobs';
const FILES_KEY = 'anime_local_files';
// Chapitres scan stockés en JSON fichier (contourne la limite 2 KB de SecureStore)
const SCAN_CHAPTERS_FILE = FileSystem.documentDirectory + 'scan_chapters.json';

interface DownloadStore {
  jobs:         ActiveJob[];
  localFiles:   LocalFile[];
  scanChapters: LocalScanChapter[];

  addJob:     (job: ActiveJob) => void;
  updateJob:  (job_id: string, patch: Partial<ActiveJob>) => void;
  removeJob:  (job_id: string) => void;

  addLocalFile:    (file: LocalFile) => void;
  removeLocalFile: (id: string) => void;

  addScanChapter:    (ch: LocalScanChapter) => void;
  removeScanChapter: (id: string) => void;
  getScanChapter:    (slug: string, scan_slug: string, num: number) => LocalScanChapter | undefined;

  loadFromStorage:  () => Promise<void>;
  saveJobs:         () => Promise<void>;
  saveFiles:        () => Promise<void>;
  saveScanChapters: () => Promise<void>;
}

export const useDownloadStore = create<DownloadStore>((set, get) => ({
  jobs:         [],
  localFiles:   [],
  scanChapters: [],

  // ── Jobs ────────────────────────────────────────────────────────────────────

  addJob: (job) => {
    set((s) => ({ jobs: [job, ...s.jobs] }));
    get().saveJobs();
  },

  updateJob: (job_id, patch) => {
    set((s) => ({
      jobs: s.jobs.map((j) => (j.job_id === job_id ? { ...j, ...patch } : j)),
    }));
    get().saveJobs();
  },

  removeJob: (job_id) => {
    set((s) => ({ jobs: s.jobs.filter((j) => j.job_id !== job_id) }));
    get().saveJobs();
  },

  // ── Fichiers vidéo/film locaux ───────────────────────────────────────────────

  addLocalFile: (file) => {
    set((s) => ({ localFiles: [file, ...s.localFiles] }));
    get().saveFiles();
  },

  removeLocalFile: (id) => {
    set((s) => ({ localFiles: s.localFiles.filter((f) => f.id !== id) }));
    get().saveFiles();
  },

  // ── Chapitres scan locaux ────────────────────────────────────────────────────

  addScanChapter: (ch) => {
    set((s) => {
      const filtered = s.scanChapters.filter((x) => x.id !== ch.id);
      return { scanChapters: [ch, ...filtered] };
    });
    get().saveScanChapters();
  },

  removeScanChapter: (id) => {
    set((s) => ({ scanChapters: s.scanChapters.filter((c) => c.id !== id) }));
    get().saveScanChapters();
  },

  getScanChapter: (slug, scan_slug, num) => {
    const id = `${slug}_${scan_slug}_${num}`;
    return get().scanChapters.find((c) => c.id === id);
  },

  // ── Persistance ─────────────────────────────────────────────────────────────

  loadFromStorage: async () => {
    try {
      const j = await SecureStore.getItemAsync(JOBS_KEY);
      const f = await SecureStore.getItemAsync(FILES_KEY);

      let scanChapters: LocalScanChapter[] = [];
      try {
        const info = await FileSystem.getInfoAsync(SCAN_CHAPTERS_FILE);
        if (info.exists) {
          const raw = await FileSystem.readAsStringAsync(SCAN_CHAPTERS_FILE);
          scanChapters = JSON.parse(raw) as LocalScanChapter[];
        }
      } catch {}

      set({
        jobs:         j ? JSON.parse(j) : [],
        localFiles:   f ? JSON.parse(f) : [],
        scanChapters,
      });
    } catch {}
  },

  saveJobs: async () => {
    try {
      const active = get().jobs.filter((j) => j.status !== 'ready');
      await SecureStore.setItemAsync(JOBS_KEY, JSON.stringify(active));
    } catch {}
  },

  saveFiles: async () => {
    try {
      await SecureStore.setItemAsync(FILES_KEY, JSON.stringify(get().localFiles));
    } catch {}
  },

  saveScanChapters: async () => {
    try {
      await FileSystem.writeAsStringAsync(
        SCAN_CHAPTERS_FILE,
        JSON.stringify(get().scanChapters),
      );
    } catch {}
  },
}));
