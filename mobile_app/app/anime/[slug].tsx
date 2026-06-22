import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  FlatList,
  Alert,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useCatalogue, useSyncContent, useRefreshCatalogue } from '@/hooks/useAnime';
import EpisodeItem from '@/components/ui/EpisodeItem';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import Badge from '@/components/ui/Badge';
import { useAuthStore } from '@/stores/authStore';
import { Saison, Video, Episode } from '@/types';

const { width, height } = Dimensions.get('window');
const HEADER_HEIGHT = height * 0.45;

export default function AnimeDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();
  const { data: catalogue, isLoading, error, refetch } = useCatalogue(slug);
  const syncMutation = useSyncContent(slug);
  const refreshMutation = useRefreshCatalogue(slug);
  const { user, isAuthenticated } = useAuthStore();

  const [selectedSaison, setSelectedSaison] = useState<Saison | null>(null);
  const [activeTab, setActiveTab] = useState<'episodes' | 'films' | 'scans'>('episodes');
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    if (catalogue?.saisons?.length) {
      setSelectedSaison(catalogue.saisons[0]);
    }
    if (catalogue?.films?.length && !catalogue?.saisons?.length) {
      setActiveTab('films');
    }
  }, [catalogue]);

  const handlePlay = (video: Video, episode: Episode) => {
    router.push({
      pathname: '/player',
      params: {
        url: video.url,
        player: video.player,
        title: catalogue?.nom,
        episode: String(episode.numero),
        saison: String(selectedSaison?.numero),
      },
    });
  };

  const handleSync = async () => {
    if (!isAuthenticated) {
      Alert.alert('Connexion requise', 'Connectez-vous pour synchroniser.');
      return;
    }
    setSyncing(true);
    try {
      await syncMutation.mutateAsync();
      Alert.alert('Succès', 'Synchronisation lancée !');
      refetch();
    } catch (e) {
      Alert.alert('Erreur', 'Impossible de synchroniser.');
    } finally {
      setSyncing(false);
    }
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
    en_cours: 'En cours',
    termine: 'Terminé',
    abandonne: 'Abandonné',
  };

  const stateColors: Record<string, string> = {
    en_cours: Colors.warning,
    termine: Colors.success,
    abandonne: Colors.textMuted,
  };

  const hasTabs = [
    catalogue.saisons?.length > 0,
    catalogue.films?.length > 0,
    catalogue.scans?.length > 0,
  ].filter(Boolean).length > 1;

  const episodes = selectedSaison?.episodes ?? [];

  return (
    <View style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false} stickyHeaderIndices={[1]}>
        {/* Hero header */}
        <View style={{ height: HEADER_HEIGHT, position: 'relative' }}>
          <Image
            source={{ uri: catalogue.image || 'https://via.placeholder.com/400x600' }}
            style={{ width: '100%', height: '100%' }}
            contentFit="cover"
          />
          <LinearGradient
            colors={['rgba(0,0,0,0.4)', 'transparent', Colors.background]}
            style={StyleSheet.absoluteFill}
          />
          <SafeAreaView style={styles.topBar} edges={['top']}>
            <Pressable style={styles.backBtn} onPress={() => router.back()}>
              <Ionicons name="chevron-back" size={24} color={Colors.text} />
            </Pressable>
            <View style={styles.topRight}>
              {isAuthenticated && user?.permissions.can_refresh && (
                <Pressable
                  style={styles.iconBtn}
                  onPress={() => refreshMutation.mutate()}
                  disabled={refreshMutation.isPending}
                >
                  <Ionicons name="refresh" size={20} color={Colors.text} />
                </Pressable>
              )}
            </View>
          </SafeAreaView>
        </View>

        {/* Sticky saison picker (index 1) */}
        {catalogue.saisons?.length > 1 && (
          <View style={styles.saisonPicker}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: Spacing.sm, paddingHorizontal: Spacing.lg }}>
              {catalogue.saisons.map((s) => (
                <Pressable
                  key={s.numero}
                  style={[styles.saisonChip, selectedSaison?.numero === s.numero && styles.saisonChipActive]}
                  onPress={() => setSelectedSaison(s)}
                >
                  <Text style={[styles.saisonChipText, selectedSaison?.numero === s.numero && styles.saisonChipTextActive]}>
                    {s.nom || `Saison ${s.numero}`}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>
          </View>
        )}

        {/* Info block */}
        <View style={styles.infoBlock}>
          <Text style={styles.animeTitle}>{catalogue.nom}</Text>

          <View style={styles.metaRow}>
            {catalogue.type && <Badge label={catalogue.type} color={Colors.primary} />}
            {catalogue.langue && <Badge label={catalogue.langue.toUpperCase()} color={Colors.accent} />}
            {catalogue.annee && <Badge label={String(catalogue.annee)} color={Colors.textSecondary} />}
            {catalogue.etat && (
              <Badge
                label={stateMap[catalogue.etat] || catalogue.etat}
                color={stateColors[catalogue.etat] || Colors.textMuted}
              />
            )}
          </View>

          {catalogue.genres?.length > 0 && (
            <View style={styles.genreRow}>
              {catalogue.genres.map((g) => (
                <View key={g} style={styles.genreTag}>
                  <Text style={styles.genreTagText}>{g}</Text>
                </View>
              ))}
            </View>
          )}

          {catalogue.synopsis && (
            <Text style={styles.synopsis} numberOfLines={4}>{catalogue.synopsis}</Text>
          )}

          {/* Sync button */}
          {isAuthenticated && !catalogue.episodes_synced && (
            <Pressable
              style={[styles.syncBtn, syncing && styles.syncBtnDisabled]}
              onPress={handleSync}
              disabled={syncing}
            >
              <Ionicons name="sync" size={16} color={Colors.text} />
              <Text style={styles.syncBtnText}>
                {syncing ? 'Synchronisation...' : 'Synchroniser les épisodes'}
              </Text>
            </Pressable>
          )}
        </View>

        {/* Tab bar (if multiple content types) */}
        {hasTabs && (
          <View style={styles.tabBar}>
            {catalogue.saisons?.length > 0 && (
              <Pressable
                style={[styles.tab, activeTab === 'episodes' && styles.tabActive]}
                onPress={() => setActiveTab('episodes')}
              >
                <Text style={[styles.tabText, activeTab === 'episodes' && styles.tabTextActive]}>
                  Épisodes ({catalogue.saisons.reduce((a, s) => a + s.episodes.length, 0)})
                </Text>
              </Pressable>
            )}
            {catalogue.films?.length > 0 && (
              <Pressable
                style={[styles.tab, activeTab === 'films' && styles.tabActive]}
                onPress={() => setActiveTab('films')}
              >
                <Text style={[styles.tabText, activeTab === 'films' && styles.tabTextActive]}>
                  Films ({catalogue.films.length})
                </Text>
              </Pressable>
            )}
            {catalogue.scans?.length > 0 && (
              <Pressable
                style={[styles.tab, activeTab === 'scans' && styles.tabActive]}
                onPress={() => setActiveTab('scans')}
              >
                <Text style={[styles.tabText, activeTab === 'scans' && styles.tabTextActive]}>
                  Scans ({catalogue.scans.length})
                </Text>
              </Pressable>
            )}
          </View>
        )}

        {/* Content */}
        <View style={styles.contentBlock}>
          {activeTab === 'episodes' && (
            <>
              {episodes.length === 0 ? (
                <View style={styles.emptyContent}>
                  <Ionicons name="film-outline" size={40} color={Colors.textMuted} />
                  <Text style={styles.emptyText}>
                    {catalogue.episodes_synced === false
                      ? 'Synchronisez pour voir les épisodes'
                      : 'Aucun épisode disponible'}
                  </Text>
                </View>
              ) : (
                episodes.map((ep, i) => (
                  <EpisodeItem key={`${ep.numero}-${i}`} episode={ep} onPlay={handlePlay} />
                ))
              )}
            </>
          )}

          {activeTab === 'films' && (
            <>
              {catalogue.films?.map((film, i) => (
                <Pressable
                  key={i}
                  style={styles.filmCard}
                  onPress={() => {
                    if (film.videos?.[0]) {
                      router.push({
                        pathname: '/player',
                        params: {
                          url: film.videos[0].url,
                          player: film.videos[0].player,
                          title: film.titre || catalogue.nom,
                        },
                      });
                    }
                  }}
                >
                  <Ionicons name="film" size={24} color={Colors.accent} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.filmTitle}>{film.titre || `Film ${i + 1}`}</Text>
                    {film.annee && <Text style={styles.filmYear}>{film.annee}</Text>}
                  </View>
                  <Ionicons name="play-circle" size={28} color={Colors.primary} />
                </Pressable>
              ))}
            </>
          )}

          {activeTab === 'scans' && (
            <View style={styles.scanInfo}>
              <Ionicons name="book-outline" size={40} color={Colors.textMuted} />
              <Text style={styles.scanText}>
                {catalogue.scans?.reduce((a, s) => a + s.chapitres.length, 0)} chapitres disponibles
              </Text>
            </View>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  topBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  topRight: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  saisonPicker: {
    backgroundColor: Colors.background,
    paddingVertical: Spacing.sm,
  },
  saisonChip: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  saisonChipActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  saisonChipText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    fontWeight: '600',
  },
  saisonChipTextActive: {
    color: Colors.text,
  },
  infoBlock: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.lg,
    gap: Spacing.md,
  },
  animeTitle: {
    color: Colors.text,
    fontSize: FontSize.xxl,
    fontWeight: '800',
    lineHeight: 30,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  genreRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.xs,
  },
  genreTag: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.sm,
  },
  genreTagText: {
    color: Colors.textSecondary,
    fontSize: FontSize.xs,
  },
  synopsis: {
    color: Colors.textSecondary,
    fontSize: FontSize.md,
    lineHeight: 22,
  },
  syncBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
    padding: Spacing.md,
  },
  syncBtnDisabled: { opacity: 0.6 },
  syncBtnText: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: '700',
  },
  tabBar: {
    flexDirection: 'row',
    marginHorizontal: Spacing.lg,
    marginTop: Spacing.xl,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.md,
    padding: 3,
  },
  tab: {
    flex: 1,
    paddingVertical: Spacing.sm,
    alignItems: 'center',
    borderRadius: Radius.sm,
  },
  tabActive: { backgroundColor: Colors.primary },
  tabText: { color: Colors.textMuted, fontSize: FontSize.sm, fontWeight: '600' },
  tabTextActive: { color: Colors.text },
  contentBlock: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.lg,
    paddingBottom: 100,
  },
  emptyContent: {
    alignItems: 'center',
    paddingVertical: Spacing.xxl,
    gap: Spacing.md,
  },
  emptyText: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
    textAlign: 'center',
  },
  filmCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    gap: Spacing.md,
  },
  filmTitle: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: '600',
  },
  filmYear: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    marginTop: 2,
  },
  scanInfo: {
    alignItems: 'center',
    paddingVertical: Spacing.xxl,
    gap: Spacing.md,
  },
  scanText: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
  },
  errorScreen: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.md,
  },
  errorTitle: {
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: '700',
  },
  backLink: {
    color: Colors.primary,
    fontSize: FontSize.md,
  },
});
