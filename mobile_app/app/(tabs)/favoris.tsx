import React, { useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  FlatList,
  RefreshControl,
  Pressable,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useAuthStore } from '@/stores/authStore';
import { useFavoris, useRecommendations } from '@/hooks/useFavorites';
import AnimeCard from '@/components/ui/AnimeCard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { RecommendationItem } from '@/types';

const { width } = Dimensions.get('window');
const CARD_WIDTH = (width - Spacing.md * 3) / 2;

// ─── Écran non connecté ───────────────────────────────────────────────────────

function NotLoggedIn() {
  const router = useRouter();
  return (
    <View style={s.centered}>
      <Ionicons name="heart-outline" size={72} color={Colors.textMuted} />
      <Text style={s.emptyTitle}>Connexion requise</Text>
      <Text style={s.emptyText}>
        Connecte-toi pour retrouver tes favoris et découvrir des recommandations personnalisées.
      </Text>
      <Pressable style={s.ctaBtn} onPress={() => router.push('/profile')}>
        <Ionicons name="person-outline" size={16} color={Colors.text} />
        <Text style={s.ctaBtnText}>Se connecter</Text>
      </Pressable>
    </View>
  );
}

// ─── État vide favoris ─────────────────────────────────────────────────────────

function EmptyFavoris() {
  return (
    <View style={s.centered}>
      <Ionicons name="heart-outline" size={64} color={Colors.textMuted} />
      <Text style={s.emptyTitle}>Aucun favori pour l'instant</Text>
      <Text style={s.emptyText}>
        Appuie sur{' '}
        <Ionicons name="heart-outline" size={13} color={Colors.textMuted} />
        {' '}sur une carte pour ajouter un catalogue à tes favoris.
      </Text>
    </View>
  );
}

// ─── Chip de genre ────────────────────────────────────────────────────────────

function GenreChip({ label }: { label: string }) {
  return (
    <View style={s.chip}>
      <Text style={s.chipText}>{label}</Text>
    </View>
  );
}

// ─── Card de recommandation (légèrement enrichie) ─────────────────────────────

function RecoCard({ item }: { item: RecommendationItem }) {
  const router = useRouter();
  const scorePercent = Math.min(Math.round(item.score * 100), 99);

  return (
    <Pressable style={s.recoCard} onPress={() => router.push(`/anime/${item.slug}`)}>
      <AnimeCard item={item} width={130} showFavori={false} />
      {item.score > 0 && (
        <View style={s.scoreBadge}>
          <Text style={s.scoreText}>{scorePercent}%</Text>
        </View>
      )}
    </Pressable>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function FavorisScreen() {
  const { isAuthenticated } = useAuthStore();

  const {
    data: favoris,
    isLoading: loadingFav,
    refetch: refetchFav,
    isRefetching: refetchingFav,
  } = useFavoris();

  const {
    data: recos,
    isLoading: loadingReco,
    refetch: refetchReco,
    isRefetching: refetchingReco,
  } = useRecommendations();

  const onRefresh = useCallback(() => {
    refetchFav();
    refetchReco();
  }, [refetchFav, refetchReco]);

  const isRefreshing = refetchingFav || refetchingReco;

  if (!isAuthenticated) {
    return (
      <SafeAreaView style={s.container} edges={['top']}>
        <View style={s.topBar}>
          <Text style={s.pageTitle}>Favoris</Text>
        </View>
        <NotLoggedIn />
      </SafeAreaView>
    );
  }

  if (loadingFav) {
    return <LoadingSpinner fullScreen message="Chargement des favoris…" />;
  }

  const catalogues = favoris?.catalogues ?? [];
  const recommendations: RecommendationItem[] = recos ?? [];

  // Genres les plus fréquents dans les favoris (pour affichage résumé)
  const genreFreq: Record<string, number> = {};
  for (const cat of catalogues) {
    for (const g of cat.genres ?? []) {
      genreFreq[g] = (genreFreq[g] ?? 0) + 1;
    }
  }
  const topGenres = Object.entries(genreFreq)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([g]) => g);

  return (
    <SafeAreaView style={s.container} edges={['top']}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={onRefresh}
            tintColor={Colors.primary}
          />
        }
      >
        {/* ── Header ── */}
        <View style={s.topBar}>
          <Text style={s.pageTitle}>Favoris</Text>
          {catalogues.length > 0 && (
            <View style={s.countBadge}>
              <Text style={s.countText}>{catalogues.length}</Text>
            </View>
          )}
        </View>

        {/* ── Genres favoris ── */}
        {topGenres.length > 0 && (
          <View style={s.genresRow}>
            {topGenres.map((g) => (
              <GenreChip key={g} label={g} />
            ))}
          </View>
        )}

        {/* ── Mes favoris ── */}
        <View style={s.sectionHeader}>
          <Ionicons name="heart" size={16} color={Colors.error} />
          <Text style={s.sectionTitle}>Mes favoris</Text>
        </View>

        {catalogues.length === 0 ? (
          <EmptyFavoris />
        ) : (
          <View style={s.grid}>
            {catalogues.map((item) => (
              <AnimeCard key={item.slug} item={item} width={CARD_WIDTH} />
            ))}
          </View>
        )}

        {/* ── Recommandations ── */}
        <View style={[s.sectionHeader, { marginTop: catalogues.length === 0 ? Spacing.lg : Spacing.xl }]}>
          <Ionicons name="sparkles" size={16} color={Colors.primary} />
          <Text style={s.sectionTitle}>Recommandations</Text>
        </View>

        {loadingReco ? (
          <View style={s.recoLoading}>
            <LoadingSpinner message="Calcul des recommandations…" />
          </View>
        ) : recommendations.length === 0 ? (
          <View style={s.recoEmpty}>
            <Text style={s.emptyText}>
              {catalogues.length === 0
                ? 'Ajoute des favoris pour obtenir des recommandations personnalisées.'
                : 'Pas encore de recommandations — essaie d\'ajouter d\'autres favoris.'}
            </Text>
          </View>
        ) : (
          <>
            <Text style={s.recoSubtitle}>
              {catalogues.length > 0
                ? `Basées sur tes genres : ${topGenres.slice(0, 3).join(', ')}`
                : 'Contenu récemment mis à jour'}
            </Text>
            <FlatList
              data={recommendations}
              horizontal
              showsHorizontalScrollIndicator={false}
              keyExtractor={(item) => item.slug}
              contentContainerStyle={s.hList}
              renderItem={({ item }) => <RecoCard item={item} />}
            />
          </>
        )}

        <View style={{ height: Spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.md,
    gap: Spacing.sm,
  },
  pageTitle: {
    color: Colors.text,
    fontSize: FontSize.xxl,
    fontWeight: '800',
  },
  countBadge: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
    minWidth: 26,
    height: 26,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.xs,
  },
  countText: {
    color: Colors.text,
    fontSize: FontSize.xs,
    fontWeight: '700',
  },
  genresRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.lg,
  },
  chip: {
    backgroundColor: Colors.primary + '22',
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.primary + '55',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
  },
  chipText: {
    color: Colors.primary,
    fontSize: FontSize.xs,
    fontWeight: '600',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.sm,
  },
  sectionTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: '700',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: Spacing.md,
    gap: Spacing.md,
    marginBottom: Spacing.sm,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing.xl,
    paddingTop: 80,
    gap: Spacing.md,
  },
  emptyTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: '700',
    textAlign: 'center',
  },
  emptyText: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    textAlign: 'center',
    lineHeight: 20,
    paddingHorizontal: Spacing.lg,
  },
  ctaBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.sm + 2,
    borderRadius: Radius.full,
    marginTop: Spacing.sm,
  },
  ctaBtnText: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: '700',
  },
  recoSubtitle: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.md,
  },
  hList: {
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
    paddingBottom: Spacing.sm,
  },
  recoCard: {
    position: 'relative',
  },
  scoreBadge: {
    position: 'absolute',
    top: Spacing.xs,
    right: Spacing.xs,
    backgroundColor: Colors.primary + 'dd',
    borderRadius: Radius.sm,
    paddingHorizontal: 5,
    paddingVertical: 2,
  },
  scoreText: {
    color: Colors.text,
    fontSize: 10,
    fontWeight: '700',
  },
  recoLoading: {
    paddingVertical: Spacing.xl,
  },
  recoEmpty: {
    paddingVertical: Spacing.lg,
  },
});
