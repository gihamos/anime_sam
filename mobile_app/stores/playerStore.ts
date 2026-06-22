import { create } from 'zustand';

export interface VideoInfo {
  url: string;
  player: string;
  title: string;
  episode?: string;
  saison?: string;
}

interface PlayerState extends VideoInfo {
  setVideo: (info: VideoInfo) => void;
  clear: () => void;
}

const EMPTY: VideoInfo = { url: '', player: '', title: '' };

export const usePlayerStore = create<PlayerState>((set) => ({
  ...EMPTY,
  setVideo: (info: VideoInfo) => set({ ...EMPTY, ...info }),
  clear: () => set(EMPTY),
}));
