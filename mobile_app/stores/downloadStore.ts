import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { ActiveJob, LocalFile } from '@/types';

const JOBS_KEY   = 'anime_active_jobs';
const FILES_KEY  = 'anime_local_files';

interface DownloadStore {
  jobs:       ActiveJob[];
  localFiles: LocalFile[];

  addJob:     (job: ActiveJob) => void;
  updateJob:  (job_id: string, patch: Partial<ActiveJob>) => void;
  removeJob:  (job_id: string) => void;

  addLocalFile:    (file: LocalFile) => void;
  removeLocalFile: (id: string) => void;

  loadFromStorage: () => Promise<void>;
  saveJobs:        () => Promise<void>;
  saveFiles:       () => Promise<void>;
}

export const useDownloadStore = create<DownloadStore>((set, get) => ({
  jobs:       [],
  localFiles: [],

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

  addLocalFile: (file) => {
    set((s) => ({ localFiles: [file, ...s.localFiles] }));
    get().saveFiles();
  },

  removeLocalFile: (id) => {
    set((s) => ({ localFiles: s.localFiles.filter((f) => f.id !== id) }));
    get().saveFiles();
  },

  loadFromStorage: async () => {
    try {
      const j = await SecureStore.getItemAsync(JOBS_KEY);
      const f = await SecureStore.getItemAsync(FILES_KEY);
      set({
        jobs:       j ? JSON.parse(j) : [],
        localFiles: f ? JSON.parse(f) : [],
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
}));
