import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  Alert,
  ActivityIndicator,
  Dimensions,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useCatalogue, useRefreshCatalogue, useSyncCatalogue, useSyncContent, useEpisodes, useSimilarCatalogues } from '@/hooks/useAnime';
import { formatCacheAge } from '@/services/catalogueCache';
import { useIsFavori, useToggleFavori } from '@/hooks/useFavorites';
import { useStartEpisodeDownload, useStartFilmDownload, useStartScanDownload } from '@/hooks/useDownloads';
import { getApiError } from '@/services/api';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import Badge from '@/components/ui/Badge';
import ScoreBadge from '@/components/ui/ScoreBadge';
import TagChip from '@/components/ui/TagChip';
import AnimeCard from '@/components/ui/AnimeCard';
import { useAuthStore } from '@/stores/authStore';
import { usePlayerStore } from '@/stores/playerStore';
import { useScanReaderStore } from '@/stores/scanReaderStore';
import { useDownloadStore } from '@/stores/downloadStore';
import { SaisonMeta, FilmMeta, Video, ScanMeta, ChapitreScan } from '@/types';

const { height } = Dimensions.get('window');
const HEADER_HEIGHT = height * 0.45;

// ─── Panneau épisodes d'une saison ───────────────────────────────────────────

function EpisodePanel({
  slug,
  saison,
  saisonIdx,
  canDownload,
  onPlay,
}: {
  slug: string;
  saison: SaisonMeta;
  saisonIdx: number;
  canDownload: boolean;
  onPlay: (video: Video, epNum: string) => void;
}) {
  // Si les épisodes sont déjà synchronisés en DB (renvoyés avec le catalogue),
  // pas besoin de rescraper en live (lent, 10-30s+) : on les utilise directement.
  const synced = saison.episodes && saison.episodes.length > 0;
  const { data: liveData, isLoading, isError, refetch } = useEpisodes(
    slug, saison.slug, saison.lang, !synced
  );
  const data = synced
    ? Object.fromEntries(saison.episodes!.map((e) => [String(e.numero), e.videos]))
    : liveData;
  const [selectedNums, setSelectedNums] = useState<Set<number>>(new Set());
  const [showDlModal, setShowDlModal] = useState(false);
  const startEpisodeDownload = useStartEpisodeDownload();
  const { jobs } = useDownloadStore();
  // Empêche de déclencher 2 fois le même téléchargement (double-tap, appui pendant
  // que la requête précédente est encore en vol) — sans ça, un épisode à 2 lecteurs
  // se retrouvait avec 2 jobs distincts créés côté serveur pour le même épisode.
  const isQueued = jobs.some((j) =>
    j.job_type === 'video' && j.slug === slug && j.saison_idx === saisonIdx
    && (j.status === 'pending' || j.status === 'downloading')
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toggleNum = (n: number) => {
    setSelectedNums((prev) => {
      const next = new Set(prev);
      next.has(n) ? next.delete(n) : next.add(n);
      return next;
    });
  };

  const handleDownload = async (nums?: number[]) => {
    if (isSubmitting || isQueued) return;
    setIsSubmitting(true);
    try {
      await startEpisodeDownload({
        slug,
        catalogueNom: slug,
        saisonIdx,
        saisonNom: saison.nom,
        nums,
      });
      setShowDlModal(false);
      Alert.alert('Téléchargement lancé', nums
        ? `${nums.length} épisode(s) ajouté(s) à la file.`
        : 'Toute la saison ajoutée à la file.'
      );
    } catch (err) {
      Alert.alert('Erreur', getApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!synced && isLoading) {
    return (
      <View style={ep.loading}>
        <ActivityIndicator color={Colors.primary} />
        <Text style={ep.loadingText}>Chargement des épisodes… (peut prendre 10-30s)</Text>
      </View>
    );
  }

  if (!synced && (isError || !data)) {
    return (
      <View style={ep.error}>
        <Text style={ep.errorText}>Impossible de charger les épisodes.</Text>
        <Pressable style={ep.retryBtn} onPress={() => refetch()}>
          <Text style={ep.retryText}>Réessayer</Text>
        </Pressable>
      </View>
    );
  }

  const epNums = Object.keys(data!).sort((a, b) => Number(a) - Number(b));
  // Titres/vignettes réels (via AniList streamingEpisodes) — présents seulement si le
  // catalogue a été synchronisé en DB avec enrichissement par épisode.
  const epEnrichment = synced
    ? Object.fromEntries(saison.episodes!.map((e) => [String(e.numero), e.enrichment]))
    : {};

  if (epNums.length === 0) {
    return (
      <View style={ep.error}>
        <Text style={ep.errorText}>Aucun épisode disponible pour cette langue.</Text>
      </View>
    );
  }

  return (
    <View>
      {canDownload && (
        <View style={ep.actionBar}>
          <Pressable
            style={[ep.dlAllBtn, (isSubmitting || isQueued) && ep.btnDisabled]}
            onPress={() => handleDownload(epNums.map(Number))}
            disabled={isSubmitting || isQueued}
          >
            {isSubmitting ? (
              <ActivityIndicator size="small" color={Colors.text} />
            ) : (
              <Ionicons name="download" size={15} color={Colors.text} />
            )}
            <Text style={ep.dlAllText}>{isQueued ? 'Déjà en cours' : 'Toute la saison'}</Text>
          </Pressable>
          <Pressable
            style={[ep.dlSelBtn, (isSubmitting || isQueued) && ep.btnDisabled]}
            onPress={() => setShowDlModal(true)}
            disabled={isSubmitting || isQueued}
          >
            <Ionicons name="checkmark-done" size={15} color={Colors.primary} />
            <Text style={ep.dlSelText}>Sélection</Text>
          </Pressable>
        </View>
      )}

      {epNums.map((num) => {
        const videos = data![num];
        const meta = epEnrichment[num];
        return (
          <View key={num} style={ep.row}>
            {meta?.thumbnail ? (
              <Image source={{ uri: meta.thumbnail }} style={ep.thumb} contentFit="cover" />
            ) : (
              <Text style={ep.epNum}>Ép. {num}</Text>
            )}
            <View style={{ flex: 1, gap: 4 }}>
              {meta?.title && (
                <Text style={ep.epTitle} numberOfLines={1}>{num}. {meta.title}</Text>
              )}
              <View style={ep.lecteurs}>
                {videos.map((v, i) => (
                  <Pressable
                    key={i}
                    style={ep.lecteurBtn}
                    onPress={() => onPlay(v, num)}
                  >
                    <Ionicons name="play-circle" size={16} color={Colors.primary} />
                    <Text style={ep.lecteurName}>{v.lecteur || `Lecteur ${i + 1}`}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          </View>
        );
      })}

      <Modal visible={showDlModal} transparent animationType="slide">
        <View style={mstyle.backdrop}>
          <View style={mstyle.sheet}>
            <Text style={mstyle.title}>Sélectionner les épisodes</Text>
            <ScrollView style={{ maxHeight: 300 }}>
              {epNums.map((num) => {
                const n = Number(num);
                const sel = selectedNums.has(n);
                return (
                  <Pressable key={num} style={mstyle.epRow} onPress={() => toggleNum(n)}>
                    <Ionicons
                      name={sel ? 'checkbox' : 'square-outline'}
                      size={20}
                      color={sel ? Colors.primary : Colors.textMuted}
                    />
                    <Text style={mstyle.epText}>Épisode {num}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
            <View style={mstyle.actions}>
              <Pressable style={mstyle.cancelBtn} onPress={() => setShowDlModal(false)}>
                <Text style={mstyle.cancelText}>Annuler</Text>
              </Pressable>
              <Pressable
                style={[mstyle.confirmBtn, (selectedNums.size === 0 || isSubmitting) && { opacity: 0.4 }]}
                disabled={selectedNums.size === 0 || isSubmitting}
                onPress={() => handleDownload(Array.from(selectedNums).sort((a, b) => a - b))}
              >
                {isSubmitting
                  ? <ActivityIndicator size="small" color={Colors.text} />
                  : <Ionicons name="download" size={16} color={Colors.text} />}
                <Text style={mstyle.confirmText}>Télécharger ({selectedNums.size})</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// ─── Panneau films ────────────────────────────────────────────────────────────

function FilmPanel({
  slug,
  film,
  filmIdx,
  canDownload,
  onPlay,
}: {
  slug: string;
  film: FilmMeta;
  filmIdx: number;
  canDownload: boolean;
  onPlay: (video: Video) => void;
}) {
  // Idem EpisodePanel : si déjà synchronisé en DB, pas de rescraping live.
  const synced = film.videos && film.videos.length > 0;
  const { data, isLoading, isError, refetch } = useEpisodes(
    slug, film.slug, film.lang, !synced
  );
  const startFilmDownload = useStartFilmDownload();
  const { jobs } = useDownloadStore();
  const isQueued = jobs.some((j) =>
    j.job_type === 'video' && j.slug === slug && j.film_idx === filmIdx
    && (j.status === 'pending' || j.status === 'downloading')
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleDownload = async () => {
    if (isSubmitting || isQueued) return;
    setIsSubmitting(true);
    try {
      await startFilmDownload({ slug, catalogueNom: slug, filmIdx, filmNom: film.nom });
      Alert.alert('Téléchargement lancé', `${film.nom} ajouté à la file.`);
    } catch (err) {
      Alert.alert('Erreur', getApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!synced && isLoading) {
    return (
      <View style={ep.loading}>
        <ActivityIndicator color={Colors.primary} />
        <Text style={ep.loadingText}>Chargement… (peut prendre 10-30s)</Text>
      </View>
    );
  }

  if (!synced && (isError || !data)) {
    return (
      <View style={ep.error}>
        <Text style={ep.errorText}>Impossible de charger ce film.</Text>
        <Pressable style={ep.retryBtn} onPress={() => refetch()}>
          <Text style={ep.retryText}>Réessayer</Text>
        </Pressable>
      </View>
    );
  }

  const videos = synced ? film.videos! : (data!['1'] ?? Object.values(data!)[0] ?? []);

  if (videos.length === 0) {
    return (
      <View style={ep.error}>
        <Text style={ep.errorText}>Aucun lecteur disponible pour ce film.</Text>
      </View>
    );
  }

  return (
    <View>
      {canDownload && (
        <View style={ep.actionBar}>
          <Pressable
            style={[ep.dlAllBtn, (isSubmitting || isQueued) && ep.btnDisabled]}
            onPress={handleDownload}
            disabled={isSubmitting || isQueued}
          >
            {isSubmitting ? (
              <ActivityIndicator size="small" color={Colors.text} />
            ) : (
              <Ionicons name="download" size={15} color={Colors.text} />
            )}
            <Text style={ep.dlAllText}>{isQueued ? 'Déjà en cours' : 'Télécharger ce film'}</Text>
          </Pressable>
        </View>
      )}
      <View style={ep.row}>
        <View style={ep.lecteurs}>
          {videos.map((v, i) => (
            <Pressable
              key={i}
              style={ep.lecteurBtn}
              onPress={() => onPlay(v)}
            >
              <Ionicons name="play-circle" size={16} color={Colors.accent} />
              <Text style={ep.lecteurName}>{v.lecteur || `Lecteur ${i + 1}`}</Text>
            </Pressable>
          ))}
        </View>
      </View>
    </View>
  );
}

// ─── Panneau scans ────────────────────────────────────────────────────────────

function ScanPanel({
  slug,
  scans,
  catalogueNom,
  canDownload,
  onOpenChapitre,
}: {
  slug: string;
  scans: ScanMeta[];
  catalogueNom: string;
  canDownload: boolean;
  onOpenChapitre: (scan: ScanMeta, chapitre: ChapitreScan, idx: number) => void;
}) {
  const [selectedScan, setSelectedScan] = useState<ScanMeta | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const startScanDownload = useStartScanDownload();
  const { getScanChapter, jobs } = useDownloadStore();

  if (scans.length === 0) {
    return (
      <View style={styles.emptyContent}>
        <Ionicons name="book-outline" size={40} color={Colors.textMuted} />
        <Text style={styles.emptyText}>
          Aucun scan disponible.{'\n'}Synchronisez le catalogue pour charger les chapitres.
        </Text>
      </View>
    );
  }

  // Un seul scan → afficher directement ses chapitres
  const activeScan = scans.length === 1 ? scans[0] : selectedScan;

  if (!activeScan) {
    return (
      <View>
        {scans.map((s) => (
          <Pressable
            key={s.slug}
            style={styles.saisonCard}
            onPress={() => setSelectedScan(s)}
          >
            <Ionicons name="book" size={20} color={Colors.vostfr} />
            <View style={{ flex: 1 }}>
              <Text style={styles.saisonNom}>{s.nom}</Text>
              <Text style={styles.saisonMeta}>
                {s.chapitres.length} chapitre{s.chapitres.length !== 1 ? 's' : ''}
                {s.lang ? ` · ${s.lang.toUpperCase()}` : ''}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
          </Pressable>
        ))}
      </View>
    );
  }

  const chapitres = [...(activeScan.chapitres ?? [])].sort((a, b) => a.numero - b.numero);

  return (
    <View>
      {scans.length > 1 && (
        <Pressable style={styles.backSaison} onPress={() => setSelectedScan(null)}>
          <Ionicons name="chevron-back" size={16} color={Colors.primary} />
          <Text style={styles.backSaisonText}>{activeScan.nom}</Text>
        </Pressable>
      )}

      {chapitres.length === 0 ? (
        <View style={styles.emptyContent}>
          <Ionicons name="book-outline" size={36} color={Colors.textMuted} />
          <Text style={styles.emptyText}>
            Chapitres non synchronisés.{'\n'}Lancez une synchronisation depuis l'admin.
          </Text>
        </View>
      ) : (
        chapitres.map((ch, idx) => {
          const hasContent  = (ch.images?.length ?? 0) > 0 || (ch.lecteurs?.length ?? 0) > 0;
          const hasImages   = (ch.images?.length ?? 0) > 0;
          const localChap   = getScanChapter(slug, activeScan.slug, ch.numero);
          const isDownloaded = !!localChap;
          const isQueued     = jobs.some(
            (j) => j.job_type === 'scan'
              && j.slug === slug
              && j.scan_slug === activeScan.slug
              && (j.chapitre_nums ?? []).includes(ch.numero)
              && (j.status === 'pending' || j.status === 'downloading')
          );

          const handleDownload = async () => {
            try {
              await startScanDownload({
                slug,
                catalogueNom,
                scanSlug:     activeScan.slug,
                scanNom:      activeScan.nom,
                chapitreNums: [ch.numero],
                chapitreLabel: ch.titre ? `Ch. ${ch.numero} — ${ch.titre}` : `Ch. ${ch.numero}`,
              });
              Alert.alert('Téléchargement lancé', `Chapitre ${ch.numero} ajouté à la file.`);
            } catch (err) {
              Alert.alert('Erreur', getApiError(err));
            }
          };

          return (
            <Pressable
              key={`${ch.numero}-${idx}`}
              style={[scan.row, !hasContent && scan.rowDisabled]}
              onPress={() => hasContent && onOpenChapitre(activeScan, ch, idx)}
              disabled={!hasContent}
            >
              <View style={scan.numBadge}>
                <Text style={scan.numText}>{ch.numero}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={scan.chapNom} numberOfLines={1}>
                  {ch.titre ? ch.titre : `Chapitre ${ch.numero}`}
                </Text>
                <View style={scan.meta}>
                  {hasImages && (
                    <View style={scan.badge}>
                      <Ionicons name="images-outline" size={11} color={Colors.success} />
                      <Text style={[scan.badgeText, { color: Colors.success }]}>
                        {ch.images.length} pages
                      </Text>
                    </View>
                  )}
                  {(ch.lecteurs?.length ?? 0) > 0 && (
                    <View style={scan.badge}>
                      <Ionicons name="globe-outline" size={11} color={Colors.primary} />
                      <Text style={[scan.badgeText, { color: Colors.primary }]}>
                        {ch.lecteurs.length} lecteur{ch.lecteurs.length > 1 ? 's' : ''}
                      </Text>
                    </View>
                  )}
                  {isDownloaded && (
                    <View style={scan.badge}>
                      <Ionicons name="cloud-done-outline" size={11} color={Colors.vostfr} />
                      <Text style={[scan.badgeText, { color: Colors.vostfr }]}>Hors ligne</Text>
                    </View>
                  )}
                  {!hasContent && (
                    <Text style={scan.unavail}>Non synchronisé</Text>
                  )}
                </View>
              </View>

              {/* Bouton téléchargement (visible si le chapitre a des images) */}
              {canDownload && hasImages && !isDownloaded && (
                <Pressable
                  style={scan.dlBtn}
                  hitSlop={12}
                  onPress={(e) => { e.stopPropagation(); handleDownload(); }}
                  disabled={isQueued}
                >
                  {isQueued
                    ? <ActivityIndicator size="small" color={Colors.primary} />
                    : <Ionicons name="download-outline" size={18} color={Colors.primary} />
                  }
                </Pressable>
              )}

              {hasContent && (
                <Ionicons name="chevron-forward" size={16} color={Colors.textMuted} />
              )}
            </Pressable>
          );
        })
      )}
    </View>
  );
}

// ─── Main screen ─────────────────────────────────────────────────────────────

export default function AnimeDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();
  const { data: catalogue, isLoading, isFetching, dataUpdatedAt, error } = useCatalogue(slug);
  const refreshMutation = useRefreshCatalogue(slug);
  const syncCatalogue   = useSyncCatalogue(slug);
  const contentSync     = useSyncContent(slug);
  const { user, isAuthenticated } = useAuthStore();
  const setVideo = usePlayerStore((s) => s.setVideo);
  const isFavori = useIsFavori(slug);
  const toggleFavori = useToggleFavori(slug);
  const startEpisodeDownload = useStartEpisodeDownload();
  const startFilmDownload = useStartFilmDownload();
  const setScanChapitre = useScanReaderStore((s) => s.setChapitre);
  const { data: similar } = useSimilarCatalogues(slug);
  const { jobs } = useDownloadStore();
  // Boutons de téléchargement rapide (icône sur la carte saison/film, hors panneau) :
  // garde locale contre le double-tap, pendant la fenêtre où le job n'est pas encore
  // dans le store (le round-trip réseau de création du job).
  const [dlBusy, setDlBusy] = useState<Set<string>>(new Set());
  const isSaisonQueued = (idx: number) => jobs.some((j) =>
    j.job_type === 'video' && j.slug === slug && j.saison_idx === idx
    && (j.status === 'pending' || j.status === 'downloading')
  );
  const isFilmQueued = (idx: number) => jobs.some((j) =>
    j.job_type === 'video' && j.slug === slug && j.film_idx === idx
    && (j.status === 'pending' || j.status === 'downloading')
  );

  // Le bouton est visible pour tout utilisateur authentifié.
  // Le serveur retourne 403 si le droit de téléchargement n'est pas accordé.
  const canDownload = isAuthenticated;

  const [selectedSaison, setSelectedSaison] = useState<SaisonMeta | null>(null);
  const [selectedFilm, setSelectedFilm] = useState<FilmMeta | null>(null);
  const [activeTab, setActiveTab] = useState<'saisons' | 'films' | 'scans'>('saisons');

  useEffect(() => {
    if (contentSync.error) Alert.alert('Synchronisation impossible', contentSync.error);
  }, [contentSync.error]);

  const handlePlay = (video: Video, extra?: { ep?: string; saison?: string }) => {
    if (!video.player_url) {
      Alert.alert('Lien introuvable', 'Aucune URL de lecture disponible pour ce contenu.');
      return;
    }
    setVideo({
      url: video.player_url,
      player: video.lecteur,
      title: catalogue?.nom ?? '',
      episode: extra?.ep,
      saison: extra?.saison,
    });
    router.push('/player');
  };

  if (isLoading) return <LoadingSpinner fullScreen message="Chargement..." />;
  if (error || !catalogue) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.errorScreen}>
          <Ionicons name="warning" size={48} color={Colors.error} />
          <Text style={styles.errorTitle}>Anime introuvable</Text>
          <Pressable onPress={() => router.back()}>
            <Text style={styles.backLink}>← Retour</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const stateMap: Record<string, string> = {
    en_cours: 'En cours', termine: 'Terminé', abandonne: 'Abandonné',
  };
  const stateColors: Record<string, string> = {
    en_cours: Colors.warning, termine: Colors.success, abandonne: Colors.textMuted,
  };
  const langColors: Record<string, string> = {
    vf: Colors.vf, vostfr: Colors.vostfr, vo: Colors.vo,
  };

  const hasSaisons = catalogue.saisons?.length > 0;
  const hasFilms   = catalogue.films?.length > 0;
  const hasScans   = catalogue.scans?.length > 0;
  const hasTabs    = [hasSaisons, hasFilms, hasScans].filter(Boolean).length > 1;

  // `activeTab` par défaut vaut 'saisons', mais un catalogue peut n'avoir que
  // des films ou que des scans (ex : manga pur) — dans ce cas il n'y a pas de
  // barre d'onglets pour en sortir. On retombe sur le premier type réellement
  // disponible plutôt que de rester bloqué sur un onglet vide.
  const availableTabs = (['saisons', 'films', 'scans'] as const).filter(
    (t) => (t === 'saisons' && hasSaisons) || (t === 'films' && hasFilms) || (t === 'scans' && hasScans)
  );
  const displayTab = availableTabs.includes(activeTab) ? activeTab : availableTabs[0];

  return (
    <View style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Hero */}
        <View style={{ height: HEADER_HEIGHT, position: 'relative' }}>
          <Image
            source={{ uri: catalogue.enrichment?.banner_url || catalogue.image }}
            style={{ width: '100%', height: '100%' }}
            contentFit="cover"
          />
          <LinearGradient
            colors={['rgba(0,0,0,0.4)', 'transparent', Colors.background]}
            style={StyleSheet.absoluteFill}
          />
          {/* Vignette poster — accent façon fiche Netflix, seulement quand on a une vraie
              bannière large (sinon poster == fond, ça ferait doublon) */}
          {catalogue.enrichment?.banner_url && catalogue.image && (
            <Image
              source={{ uri: catalogue.image }}
              style={styles.posterThumb}
              contentFit="cover"
            />
          )}
          <SafeAreaView style={styles.topBar} edges={['top']}>
            <Pressable style={styles.backBtn} onPress={() => router.back()}>
              <Ionicons name="chevron-back" size={24} color={Colors.text} />
            </Pressable>
            <View style={styles.topRight}>
              {isAuthenticated && (
                <Pressable style={styles.iconBtn} onPress={() => toggleFavori.mutate()}>
                  <Ionicons
                    name={isFavori ? 'heart' : 'heart-outline'}
                    size={22}
                    color={isFavori ? Colors.error : Colors.text}
                  />
                </Pressable>
              )}
              {/* Sync local — disponible pour tous les utilisateurs authentifiés */}
              {isAuthenticated && (
                <Pressable
                  style={styles.iconBtn}
                  onPress={syncCatalogue}
                  disabled={isFetching}
                >
                  {isFetching
                    ? <ActivityIndicator size="small" color={Colors.primary} />
                    : <Ionicons name="sync-outline" size={20} color={Colors.text} />
                  }
                </Pressable>
              )}
              {/* Refresh admin — re-scrape les sources */}
              {isAuthenticated && user?.permissions?.can_refresh && (
                <Pressable
                  style={styles.iconBtn}
                  onPress={() => refreshMutation.mutate()}
                  disabled={refreshMutation.isPending}
                >
                  {refreshMutation.isPending
                    ? <ActivityIndicator size="small" color={Colors.warning} />
                    : <Ionicons name="cloud-download-outline" size={20} color={Colors.text} />
                  }
                </Pressable>
              )}
              {/* Sync contenu — scrape complet des épisodes/films/scans, peut prendre plusieurs minutes */}
              {isAuthenticated && user?.permissions?.can_sync && (
                <Pressable
                  style={styles.iconBtn}
                  onPress={() => contentSync.start()}
                  disabled={contentSync.isSyncing}
                >
                  {contentSync.isSyncing
                    ? <ActivityIndicator size="small" color={Colors.vostfr} />
                    : <Ionicons name="download-outline" size={20} color={Colors.text} />
                  }
                </Pressable>
              )}
            </View>
          </SafeAreaView>
        </View>

        {/* Info */}
        <View style={styles.infoBlock}>
          <Text style={styles.animeTitle}>{catalogue.nom}</Text>
          {catalogue.titre_alternatif && (
            <Text style={styles.altTitle}>{catalogue.titre_alternatif}</Text>
          )}
          {dataUpdatedAt > 0 && (
            <Text style={styles.cacheAge}>
              {isFetching ? 'Synchronisation…' : `Données : ${formatCacheAge(dataUpdatedAt)}`}
            </Text>
          )}
          <View style={styles.metaRow}>
            {catalogue.type_contenu && <Badge label={catalogue.type_contenu} color={Colors.primary} />}
            {catalogue.etat && (
              <Badge
                label={stateMap[catalogue.etat] || catalogue.etat}
                color={stateColors[catalogue.etat] || Colors.textMuted}
              />
            )}
            {catalogue.langues?.map((l) => (
              <Badge key={l} label={l.toUpperCase()} color={langColors[l] || Colors.textSecondary} />
            ))}
            <ScoreBadge enrichment={catalogue.enrichment} size="md" />
          </View>
          {(() => {
            // dédoublonnage défensif : le scraping peut renvoyer un genre plusieurs fois.
            // genres_fr (AniList) préférés s'ils existent, sinon repli sur les genres bruts.
            const genresDisplay = catalogue.enrichment?.genres_fr?.length
              ? catalogue.enrichment.genres_fr
              : catalogue.genres ?? [];
            return genresDisplay.length > 0 ? (
              <View style={styles.genreRow}>
                {[...new Set(genresDisplay)].map((g) => <TagChip key={g} label={g} />)}
              </View>
            ) : null;
          })()}
          {catalogue.enrichment?.studios_ou_staff && catalogue.enrichment.studios_ou_staff.length > 0 && (
            <Text style={styles.studioLine}>
              {catalogue.enrichment.type === 'MANGA' ? 'Auteur : ' : 'Studio : '}
              {catalogue.enrichment.studios_ou_staff.join(', ')}
            </Text>
          )}
          {(catalogue.enrichment?.synopsis_fr || catalogue.synopsis) && (
            <Text style={styles.synopsis} numberOfLines={4}>
              {catalogue.enrichment?.synopsis_fr || catalogue.synopsis}
            </Text>
          )}
          {catalogue.enrichment?.tags && catalogue.enrichment.tags.length > 0 && (
            <View style={styles.genreRow}>
              {[...catalogue.enrichment.tags]
                .sort((a, b) => b.rank - a.rank)
                .slice(0, 6)
                .map((t) => <TagChip key={t.name} label={t.name} variant="outline" />)}
            </View>
          )}
        </View>

        {contentSync.isSyncing && (
          <View style={styles.syncBanner}>
            <ActivityIndicator size="small" color={Colors.vostfr} />
            <View style={{ flex: 1 }}>
              <Text style={styles.syncBannerText}>
                Synchronisation du contenu… {contentSync.status?.progress ?? 0}%
              </Text>
              {contentSync.status?.message && (
                <Text style={styles.syncBannerSub} numberOfLines={1}>{contentSync.status.message}</Text>
              )}
            </View>
          </View>
        )}

        {/* Tabs */}
        {hasTabs && (
          <View style={styles.tabBar}>
            {hasSaisons && (
              <Pressable
                style={[styles.tab, displayTab === 'saisons' && styles.tabActive]}
                onPress={() => { setActiveTab('saisons'); setSelectedSaison(null); }}
              >
                <Text style={[styles.tabText, displayTab === 'saisons' && styles.tabTextActive]}>
                  Saisons ({catalogue.saisons.length})
                </Text>
              </Pressable>
            )}
            {hasFilms && (
              <Pressable
                style={[styles.tab, displayTab === 'films' && styles.tabActive]}
                onPress={() => { setActiveTab('films'); setSelectedFilm(null); }}
              >
                <Text style={[styles.tabText, displayTab === 'films' && styles.tabTextActive]}>
                  Films ({catalogue.films.length})
                </Text>
              </Pressable>
            )}
            {hasScans && (
              <Pressable
                style={[styles.tab, displayTab === 'scans' && styles.tabActive]}
                onPress={() => setActiveTab('scans')}
              >
                <Text style={[styles.tabText, displayTab === 'scans' && styles.tabTextActive]}>
                  Scans
                </Text>
              </Pressable>
            )}
          </View>
        )}

        {/* Content */}
        <View style={styles.contentBlock}>

          {/* ── Saisons ── */}
          {displayTab === 'saisons' && (
            <>
              {!hasSaisons && (
                <Text style={styles.emptyText}>Aucune saison disponible.</Text>
              )}
              {!selectedSaison && hasSaisons && (
                catalogue.saisons.map((s, idx) => (
                  <Pressable
                    key={`${s.slug}-${s.lang}`}
                    style={styles.saisonCard}
                    onPress={() => setSelectedSaison(s)}
                  >
                    <View style={[styles.langDot, { backgroundColor: langColors[s.lang] || Colors.primary }]} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.saisonNom}>{s.nom}</Text>
                      <Text style={styles.saisonMeta}>
                        {s.total_episodes} épisodes · {s.lang.toUpperCase()}
                      </Text>
                    </View>
                    {canDownload && (() => {
                      const key = `saison-${idx}`;
                      const busy = dlBusy.has(key) || isSaisonQueued(idx);
                      return (
                        <Pressable
                          style={styles.dlIconBtn}
                          hitSlop={12}
                          disabled={busy}
                          onPress={(e) => {
                            e.stopPropagation();
                            if (busy) return;
                            setDlBusy((prev) => new Set(prev).add(key));
                            startEpisodeDownload({
                              slug,
                              catalogueNom: catalogue.nom,
                              saisonIdx: idx,
                              saisonNom: s.nom,
                            }).then(() =>
                              Alert.alert('Téléchargement lancé', `${s.nom} ajoutée à la file.`)
                            ).catch((err) =>
                              Alert.alert('Erreur', getApiError(err))
                            ).finally(() =>
                              setDlBusy((prev) => { const next = new Set(prev); next.delete(key); return next; })
                            );
                          }}
                        >
                          {busy
                            ? <ActivityIndicator size="small" color={Colors.primary} />
                            : <Ionicons name="download-outline" size={18} color={Colors.primary} />}
                        </Pressable>
                      );
                    })()}
                    <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
                  </Pressable>
                ))
              )}
              {selectedSaison && (
                <>
                  <Pressable style={styles.backSaison} onPress={() => setSelectedSaison(null)}>
                    <Ionicons name="chevron-back" size={16} color={Colors.primary} />
                    <Text style={styles.backSaisonText}>{selectedSaison.nom}</Text>
                  </Pressable>
                  <EpisodePanel
                    slug={slug}
                    saison={selectedSaison}
                    saisonIdx={catalogue.saisons.findIndex(
                      (s) => s.slug === selectedSaison.slug && s.lang === selectedSaison.lang
                    )}
                    canDownload={canDownload}
                    onPlay={(video, num) =>
                      handlePlay(video, { ep: num, saison: selectedSaison.nom })
                    }
                  />
                </>
              )}
            </>
          )}

          {/* ── Films ── */}
          {displayTab === 'films' && (
            <>
              {!selectedFilm && (
                catalogue.films.map((f, idx) => (
                  <Pressable
                    key={`${f.slug}-${f.lang}`}
                    style={styles.saisonCard}
                    onPress={() => setSelectedFilm(f)}
                  >
                    <Ionicons name="film" size={20} color={Colors.accent} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.saisonNom}>{f.nom}</Text>
                      <Text style={styles.saisonMeta}>{f.lang.toUpperCase()}</Text>
                    </View>
                    {canDownload && (() => {
                      const key = `film-${idx}`;
                      const busy = dlBusy.has(key) || isFilmQueued(idx);
                      return (
                        <Pressable
                          style={styles.dlIconBtn}
                          hitSlop={12}
                          disabled={busy}
                          onPress={(e) => {
                            e.stopPropagation();
                            if (busy) return;
                            setDlBusy((prev) => new Set(prev).add(key));
                            startFilmDownload({
                              slug,
                              catalogueNom: catalogue.nom,
                              filmIdx: idx,
                              filmNom: f.nom,
                            }).then(() =>
                              Alert.alert('Téléchargement lancé', `${f.nom} ajouté à la file.`)
                            ).catch((err) =>
                              Alert.alert('Erreur', getApiError(err))
                            ).finally(() =>
                              setDlBusy((prev) => { const next = new Set(prev); next.delete(key); return next; })
                            );
                          }}
                        >
                          {busy
                            ? <ActivityIndicator size="small" color={Colors.accent} />
                            : <Ionicons name="download-outline" size={18} color={Colors.accent} />}
                        </Pressable>
                      );
                    })()}
                    <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
                  </Pressable>
                ))
              )}
              {selectedFilm && (
                <>
                  <Pressable style={styles.backSaison} onPress={() => setSelectedFilm(null)}>
                    <Ionicons name="chevron-back" size={16} color={Colors.primary} />
                    <Text style={styles.backSaisonText}>{selectedFilm.nom}</Text>
                  </Pressable>
                  <FilmPanel
                    slug={slug}
                    film={selectedFilm}
                    filmIdx={catalogue.films.findIndex(
                      (f) => f.slug === selectedFilm.slug && f.lang === selectedFilm.lang
                    )}
                    canDownload={canDownload}
                    onPlay={(video) => handlePlay(video)}
                  />
                </>
              )}
            </>
          )}

          {/* ── Scans ── */}
          {displayTab === 'scans' && (
            <ScanPanel
              slug={slug}
              scans={catalogue.scans}
              catalogueNom={catalogue.nom}
              canDownload={canDownload}
              onOpenChapitre={(scan, chapitre, idx) => {
                setScanChapitre({
                  chapitre,
                  chapitres:     scan.chapitres,
                  chapitreIndex: idx,
                  catalogueNom:  catalogue.nom,
                  catalogueSlug: slug,
                  scanNom:       scan.nom,
                  scanSlug:      scan.slug,
                });
                router.push('/scan-reader');
              }}
            />
          )}
        </View>

        {/* ── Titres similaires ── */}
        {similar && similar.length > 0 && (
          <View style={styles.similarSection}>
            <View style={styles.sectionTitleRow}>
              <Ionicons name="albums-outline" size={16} color={Colors.primary} />
              <Text style={styles.sectionTitle}>Titres similaires</Text>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.similarList}>
              {similar.map((item) => (
                <AnimeCard key={item.slug} item={item} width={120} reason={item.reason} showFavori={false} />
              ))}
            </ScrollView>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: Colors.background },
  topBar: {
    position: 'absolute', top: 0, left: 0, right: 0,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: Spacing.md,
  },
  topRight: { flexDirection: 'row', gap: Spacing.sm },
  backBtn: {
    width: 40, height: 40, borderRadius: Radius.full,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center', alignItems: 'center',
  },
  iconBtn: {
    width: 40, height: 40, borderRadius: Radius.full,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center', alignItems: 'center',
  },
  dlIconBtn: {
    width: 34, height: 34, borderRadius: Radius.full,
    backgroundColor: Colors.primary + '22',
    justifyContent: 'center', alignItems: 'center',
  },
  infoBlock: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.lg, gap: Spacing.md },
  syncBanner: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    marginHorizontal: Spacing.lg, marginTop: Spacing.md,
    padding: Spacing.sm, borderRadius: Radius.md,
    backgroundColor: Colors.vostfr + '1a',
  },
  syncBannerText: { color: Colors.text, fontSize: FontSize.sm, fontWeight: '600' },
  syncBannerSub:  { color: Colors.textMuted, fontSize: FontSize.xs, marginTop: 2 },
  animeTitle: { color: Colors.text, fontSize: FontSize.xxl, fontWeight: '800', lineHeight: 30 },
  altTitle:   { color: Colors.textMuted, fontSize: FontSize.sm },
  cacheAge:   { color: Colors.textMuted, fontSize: FontSize.xs, fontStyle: 'italic' },
  metaRow:    { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, alignItems: 'center' },
  genreRow:   { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  studioLine: { color: Colors.textMuted, fontSize: FontSize.sm },
  synopsis:   { color: Colors.textSecondary, fontSize: FontSize.md, lineHeight: 22 },
  posterThumb: {
    position: 'absolute', bottom: Spacing.lg, left: Spacing.lg,
    width: 76, height: 108, borderRadius: Radius.md,
    borderWidth: 2, borderColor: Colors.background,
  },
  tabBar: {
    flexDirection: 'row', marginHorizontal: Spacing.lg, marginTop: Spacing.xl,
    backgroundColor: Colors.surfaceAlt, borderRadius: Radius.md, padding: 3,
  },
  tab:           { flex: 1, paddingVertical: Spacing.sm, alignItems: 'center', borderRadius: Radius.sm },
  tabActive:     { backgroundColor: Colors.primary },
  tabText:       { color: Colors.textMuted, fontSize: FontSize.sm, fontWeight: '600' },
  tabTextActive: { color: Colors.text },
  contentBlock:  { paddingHorizontal: Spacing.lg, paddingTop: Spacing.lg, paddingBottom: 100, gap: Spacing.sm },
  saisonCard: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md,
    backgroundColor: Colors.card, borderRadius: Radius.md,
    padding: Spacing.md, borderWidth: 1, borderColor: Colors.border,
  },
  saisonNom:  { color: Colors.text, fontSize: FontSize.md, fontWeight: '600' },
  saisonMeta: { color: Colors.textMuted, fontSize: FontSize.xs, marginTop: 2 },
  langDot:    { width: 8, height: 8, borderRadius: 4 },
  backSaison: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.xs,
    marginBottom: Spacing.md,
  },
  backSaisonText: { color: Colors.primary, fontSize: FontSize.md, fontWeight: '600' },
  emptyContent: { alignItems: 'center', paddingVertical: Spacing.xxl, gap: Spacing.md },
  emptyText:    { color: Colors.textMuted, fontSize: FontSize.md, textAlign: 'center' },
  errorScreen:  { flex: 1, alignItems: 'center', justifyContent: 'center', gap: Spacing.md },
  errorTitle:   { color: Colors.text, fontSize: FontSize.xl, fontWeight: '700' },
  backLink:     { color: Colors.primary, fontSize: FontSize.md },
  similarSection: { marginTop: Spacing.lg, marginBottom: Spacing.xxl, gap: Spacing.md },
  sectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs, paddingHorizontal: Spacing.lg },
  sectionTitle: { color: Colors.text, fontSize: FontSize.lg, fontWeight: '700' },
  similarList:  { paddingHorizontal: Spacing.lg, gap: Spacing.sm },
});

const ep = StyleSheet.create({
  loading:     { alignItems: 'center', padding: Spacing.xl, gap: Spacing.md },
  loadingText: { color: Colors.textMuted, fontSize: FontSize.sm, textAlign: 'center' },
  error:       { alignItems: 'center', padding: Spacing.lg, gap: Spacing.sm },
  errorText:   { color: Colors.textMuted, fontSize: FontSize.sm, textAlign: 'center' },
  retryBtn: {
    backgroundColor: Colors.primary + '33', borderRadius: Radius.full,
    paddingVertical: Spacing.sm, paddingHorizontal: Spacing.lg,
    borderWidth: 1, borderColor: Colors.primary,
  },
  retryText: { color: Colors.primary, fontSize: FontSize.sm, fontWeight: '600' },
  actionBar: { flexDirection: 'row', gap: Spacing.sm, marginBottom: Spacing.md },
  dlAllBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: Colors.primary, borderRadius: Radius.full,
    paddingVertical: Spacing.sm, paddingHorizontal: Spacing.md,
    flex: 1, justifyContent: 'center',
  },
  dlAllText: { color: Colors.text, fontSize: FontSize.sm, fontWeight: '600' },
  dlSelBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: Colors.primary + '22', borderRadius: Radius.full,
    paddingVertical: Spacing.sm, paddingHorizontal: Spacing.md,
    flex: 1, justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.primary,
  },
  dlSelText: { color: Colors.primary, fontSize: FontSize.sm, fontWeight: '600' },
  btnDisabled: { opacity: 0.5 },
  row: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  epNum:    { color: Colors.textSecondary, fontSize: FontSize.sm, fontWeight: '600', width: 48 },
  thumb:    { width: 72, height: 44, borderRadius: Radius.sm, backgroundColor: Colors.surfaceAlt },
  epTitle:  { color: Colors.text, fontSize: FontSize.sm, fontWeight: '600' },
  lecteurs: { flex: 1, flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  lecteurBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.primary + '22',
    borderRadius: Radius.full,
    paddingVertical: 4, paddingHorizontal: Spacing.sm,
  },
  lecteurName: { color: Colors.primary, fontSize: FontSize.xs, fontWeight: '600' },
});

const scan = StyleSheet.create({
  row: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  rowDisabled: { opacity: 0.4 },
  numBadge: {
    width: 44, height: 44, borderRadius: Radius.sm,
    backgroundColor: Colors.surfaceAlt,
    justifyContent: 'center', alignItems: 'center',
  },
  numText:  { color: Colors.primary, fontSize: FontSize.sm, fontWeight: '700' },
  chapNom:  { color: Colors.text, fontSize: FontSize.sm, fontWeight: '600' },
  meta:     { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs, marginTop: 4 },
  badge: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.full,
    paddingHorizontal: 6, paddingVertical: 2,
  },
  badgeText: { fontSize: FontSize.xs, fontWeight: '600' },
  unavail:   { color: Colors.textMuted, fontSize: FontSize.xs, fontStyle: 'italic' },
  dlBtn:     { padding: Spacing.xs, marginRight: Spacing.xs },
});

const mstyle = StyleSheet.create({
  backdrop: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: Colors.card, borderTopLeftRadius: Radius.xl,
    borderTopRightRadius: Radius.xl, padding: Spacing.lg, gap: Spacing.md,
  },
  title:   { color: Colors.text, fontSize: FontSize.lg, fontWeight: '700' },
  epRow:   { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.sm },
  epText:  { color: Colors.text, fontSize: FontSize.md },
  actions: { flexDirection: 'row', gap: Spacing.md, marginTop: Spacing.sm },
  cancelBtn: {
    flex: 1, paddingVertical: Spacing.md, alignItems: 'center',
    backgroundColor: Colors.surfaceAlt, borderRadius: Radius.md,
  },
  cancelText: { color: Colors.textMuted, fontWeight: '600' },
  confirmBtn: {
    flex: 2, paddingVertical: Spacing.md, flexDirection: 'row',
    alignItems: 'center', justifyContent: 'center', gap: Spacing.sm,
    backgroundColor: Colors.primary, borderRadius: Radius.md,
  },
  confirmText: { color: Colors.text, fontWeight: '700', fontSize: FontSize.md },
});
