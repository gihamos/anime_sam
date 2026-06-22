import { create } from 'zustand';
import { ChapitreScan, LecteurScan } from '@/types';

interface ScanReaderState {
  // Données du chapitre en cours
  chapitre: ChapitreScan | null;
  catalogueNom: string;
  scanNom: string;
  // Index du chapitre dans la liste (pour navigation prev/next)
  chapitres: ChapitreScan[];
  chapitreIndex: number;

  setChapitre: (params: {
    chapitre: ChapitreScan;
    chapitres: ChapitreScan[];
    chapitreIndex: number;
    catalogueNom: string;
    scanNom: string;
  }) => void;
  goToNext: () => void;
  goToPrev: () => void;
  clear: () => void;
}

export const useScanReaderStore = create<ScanReaderState>((set, get) => ({
  chapitre: null,
  catalogueNom: '',
  scanNom: '',
  chapitres: [],
  chapitreIndex: 0,

  setChapitre: ({ chapitre, chapitres, chapitreIndex, catalogueNom, scanNom }) =>
    set({ chapitre, chapitres, chapitreIndex, catalogueNom, scanNom }),

  goToNext: () => {
    const { chapitres, chapitreIndex } = get();
    const next = chapitreIndex + 1;
    if (next < chapitres.length) {
      set({ chapitre: chapitres[next], chapitreIndex: next });
    }
  },

  goToPrev: () => {
    const { chapitres, chapitreIndex } = get();
    const prev = chapitreIndex - 1;
    if (prev >= 0) {
      set({ chapitre: chapitres[prev], chapitreIndex: prev });
    }
  },

  clear: () => set({ chapitre: null, catalogueNom: '', scanNom: '', chapitres: [], chapitreIndex: 0 }),
}));
