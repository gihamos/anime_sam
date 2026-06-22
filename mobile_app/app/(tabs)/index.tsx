import React, { useMemo, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ScrollView,
  Pressable,
  Dimensions,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useCatalogueList } from '@/hooks/useAnime';
import AnimeCard from '@/components/ui/AnimeCard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { useAuthStore } from '@/stores/authStore';
import { CatalogueSummary } from '@/types';

const { width } = Dimensions.get('window');
const HERO_HEIGHT = 440;
const HERO_ROTATE_MS = 4500;

function typeColor(type?: string) {
  if (type === 'film') return Colors.accent;
  if (type === 'scan') return Colors.success;
  return Colors.primary;
}

function typeLabel(cat: CatalogueSummary) {
  const t = cat.type_contenu ?? cat.type ?? '';
  if (t === 'film')  return 'FILM';
  if (t === 'scan')  return 'SCAN';
  if (t === 'anime') return 'ANIMÉ';
  return t.toUpperCase();
}

// ─── Hero carousel ────────────────────────────────────────────────────────────

function HeroSection({ items }: { items: CatalogueSummary[] }) {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [idx, setIdx] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (items.length < 2) return;
    timerRef.current = setInterval(() => {
      setIdx((i) => (i + 1) % items.length);
    }, HERO_ROTATE_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [items.length]);

  const hero = items[idx];
  if (!hero) return null;

  const tc = hero.type_contenu ?? hero.type ?? '';
  const tc2 = typeColor(tc);

  return (
    <View style={styles.hero}>
      <Image
        source={{ uri: hero.image || '' }}
        style={styles.heroImage}
        contentFit="cover"
        transition={400}
      />
      <LinearGradient
        colors={['transparent', 'rgba(10,10,15,0.55)', Colors.background]}
        style={styles.heroGradient}
      />

      {/* Badges haut */}
      <View style={styles.heroBadgesTop}>
        {tc && (
          <View style={[styles.heroBadge, { backgroundColor: tc2 + 'cc' }]}>
            <Text style={styles.heroBadgeText}>{typeLabel(hero)}</Text>
          </View>
        )}
        {hero.etat === 'en_cours' && (
          <View style={[styles.heroBadge, { backgroundColor: Colors.warning + 'cc' }]}>
            <View style={styles.liveDot} />
            <Text style={styles.heroBadgeText}>EN COURS</Text>
          </View>
        )}
        {hero.note != null && hero.note > 0 && (
          <View style={[styles.heroBadge, { backgroundColor: 'rgba(0,0,0,0.55)' }]}>
            <Ionicons name="star" size={11} color={Colors.warning} />
            <Text style={[styles.heroBadgeText, { color: Colors.warning }]}>
              {' '}{hero.note.toFixed(1)}
            </Text>
          </View>
        )}
      </View>

      {/* Contenu bas */}
      <View style={styles.heroContent}>
        <Text style={styles.heroTitle} numberOfLines={2}>{hero.nom}</Text>
        {hero.genres.length > 0 && (
          <Text style={styles.heroGenres}>{hero.genres.slice(0, 3).join(' · ')}</Text>
        )}
        <View style={styles.heroActions}>
          <Pressable
            style={styles.heroBtn}
            onPress={() => router.push(`/anime/${hero.slug}`)}
          >
            <Ionicons name="play" size={14} color={Colors.text} />
            <Text style={styles.heroBtnText}>Regarder</Text>
          </Pressable>
          <Pressable
            style={styles.heroBtnSecondary}
            onPress={() => router.push(`/anime/${hero.slug}`)}
          >
            <Ionicons name="information-circle-outline" size={14} color={Colors.textSecondary} />
            <Text style={styles.heroBtnSecondaryText}>Plus d'infos</Text>
          </Pressable>
        </View>
      </View>

      {/* Dots pagination */}
      <View style={styles.heroDots}>
        {items.map((_, i) => (
          <Pressable key={i} onPress={() => setIdx(i)} hitSlop={6}>
            <View style={[styles.dot, i === idx && styles.dotActive]} />
          </Pressable>
        ))}
      </View>
    </View>
  );
}

// ─── Section horizontale ──────────────────────────────────────────────────────

function HRow({
  title,
  icon,
  items,
  cardWidth = 120,
  seeAllParams,
}: {
  title: string;
  icon: React.ComponentProps<typeof Ionicons>['name'];
  items: CatalogueSummary[];
  cardWidth?: number;
  seeAllParams?: Record<string, string>;
}) {
  const router = useRouter();
  if (items.length === 0) return null;
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <View style={styles.sectionTitleRow}>
          <Ionicons name={icon} size={16} color={Colors.primary} />
          <Text style={styles.sectionTitle}>{title}</Text>
          <View style={styles.countChip}>
            <Text style={styles.countChipText}>{items.length}</Text>
          </View>
        </View>
        {seeAllParams && (
          <Pressable onPress={() => router.push({ pathname: '/(tabs)/search', params: seeAllParams })}>
            <Text style={styles.seeAll}>Tout voir</Text>
          </Pressable>
        )}
      </View>
      <FlatList
        data={items}
        horizontal
        showsHorizontalScrollIndicator={false}
        keyExtractor={(item) => item.slug}
        contentContainerStyle={styles.hList}
        renderItem={({ item }) => <AnimeCard item={item} width={cardWidth} />}
      />
    </View>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();
  const { data: catalogues, isLoading, refetch, isRefetching } = useCatalogueList();

  useEffect(() => { refetch(); }, [isAuthenticated]);

  const sorted = useMemo(() => {
    const all = catalogues ?? [];

    // Hero : mieux notés (note desc), sinon les plus récemment mis à jour
    const heroItems = [...all]
      .sort((a, b) => {
        const nd = (b.note ?? 0) - (a.note ?? 0);
        if (nd !== 0) return nd;
        return (b.updated_at ?? '') > (a.updated_at ?? '') ? 1 : -1;
      })
      .slice(0, 8);

    // En cours de diffusion : en_cours, trié par updated_at desc
    const ongoing = all
      .filter((c) => c.etat === 'en_cours')
      .sort((a, b) => ((b.updated_at ?? '') > (a.updated_at ?? '') ? 1 : -1))
      .slice(0, 15);

    // Mieux notés : note > 0, trié note desc
    const topRated = all
      .filter((c) => (c.note ?? 0) > 0)
      .sort((a, b) => (b.note ?? 0) - (a.note ?? 0))
      .slice(0, 15);

    // Nouveautés : créés récemment (created_at desc)
    const newArrivals = [...all]
      .sort((a, b) => ((b.created_at ?? '') > (a.created_at ?? '') ? 1 : -1))
      .slice(0, 15);

    // Films
    const films = all
      .filter((c) => (c.type_contenu ?? c.type) === 'film')
      .sort((a, b) => ((b.updated_at ?? '') > (a.updated_at ?? '') ? 1 : -1))
      .slice(0, 15);

    // Scans & manga
    const scans = all
      .filter((c) => (c.type_contenu ?? c.type) === 'scan')
      .sort((a, b) => ((b.updated_at ?? '') > (a.updated_at ?? '') ? 1 : -1))
      .slice(0, 15);

    return { heroItems, ongoing, topRated, newArrivals, films, scans };
  }, [catalogues]);

  if (isLoading) return <LoadingSpinner fullScreen message="Chargement du catalogue..." />;

  const all = catalogues ?? [];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={Colors.primary} />
        }
      >
        {/* ── Header ── */}
        <View style={styles.header}>
          <View>
            <Text style={styles.logo}>Anime Sama</Text>
            {isAuthenticated && user && (
              <Text style={styles.greeting}>Bonjour, {user.username} 👋</Text>
            )}
          </View>
          <Pressable onPress={() => router.push('/search')} style={styles.searchBtn}>
            <Ionicons name="search" size={20} color={Colors.textSecondary} />
          </Pressable>
        </View>

        {/* ── Hero carousel ── */}
        {sorted.heroItems.length > 0 && <HeroSection items={sorted.heroItems} />}

        {/* ── En cours de diffusion ── */}
        <HRow
          title="En cours de diffusion"
          icon="radio-button-on"
          items={sorted.ongoing}
          seeAllParams={{ etat: 'en_cours' }}
        />

        {/* ── Mieux notés ── */}
        <HRow
          title="Les mieux notés"
          icon="star"
          items={sorted.topRated}
        />

        {/* ── Nouveautés ── */}
        <HRow
          title="Nouveautés"
          icon="sparkles"
          items={sorted.newArrivals}
        />

        {/* ── Films ── */}
        {sorted.films.length > 0 && (
          <HRow
            title="Films"
            icon="film"
            items={sorted.films}
            seeAllParams={{ type: 'film' }}
          />
        )}

        {/* ── Scans & Manga ── */}
        {sorted.scans.length > 0 && (
          <HRow
            title="Scans & Manga"
            icon="book"
            items={sorted.scans}
            seeAllParams={{ type: 'scan' }}
          />
        )}

        {/* ── Tout le catalogue (grille) ── */}
        <View style={styles.gridSection}>
          <View style={styles.sectionHeader}>
            <View style={styles.sectionTitleRow}>
              <Ionicons name="grid" size={16} color={Colors.primary} />
              <Text style={styles.sectionTitle}>Tout le catalogue</Text>
              <View style={styles.countChip}>
                <Text style={styles.countChipText}>{all.length}</Text>
              </View>
            </View>
          </View>
          <View style={styles.grid}>
            {all.map((item) => (
              <AnimeCard key={item.slug} item={item} />
            ))}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: Colors.background },

  header: {
    flexDirection:  'row',
    alignItems:     'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    paddingTop:     Spacing.sm,
    paddingBottom:  Spacing.md,
  },
  logo: {
    color:      Colors.text,
    fontSize:   FontSize.xxl,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  greeting: {
    color:      Colors.textMuted,
    fontSize:   FontSize.sm,
    marginTop:  2,
  },
  searchBtn: {
    width:           40,
    height:          40,
    borderRadius:    Radius.full,
    backgroundColor: Colors.surfaceAlt,
    borderWidth:     1,
    borderColor:     Colors.border,
    justifyContent:  'center',
    alignItems:      'center',
  },

  // ── Hero ──
  hero: {
    height:         HERO_HEIGHT,
    position:       'relative',
    marginBottom:   Spacing.xl,
  },
  heroImage: {
    width:  '100%',
    height: '100%',
  },
  heroGradient: {
    position: 'absolute',
    bottom:   0,
    left:     0,
    right:    0,
    height:   '80%',
  },
  heroBadgesTop: {
    position:      'absolute',
    top:           Spacing.md,
    left:          Spacing.lg,
    flexDirection: 'row',
    gap:           Spacing.xs,
  },
  heroBadge: {
    flexDirection:    'row',
    alignItems:       'center',
    paddingHorizontal: Spacing.sm,
    paddingVertical:  4,
    borderRadius:     Radius.sm,
    gap:              4,
  },
  heroBadgeText: {
    color:       Colors.text,
    fontSize:    FontSize.xs,
    fontWeight:  '700',
    letterSpacing: 0.5,
  },
  liveDot: {
    width:           6,
    height:          6,
    borderRadius:    Radius.full,
    backgroundColor: Colors.warning,
  },
  heroContent: {
    position: 'absolute',
    bottom:   Spacing.xxl,
    left:     Spacing.lg,
    right:    Spacing.lg,
  },
  heroTitle: {
    color:      Colors.text,
    fontSize:   FontSize.xxxl,
    fontWeight: '800',
    lineHeight: 38,
    marginBottom: Spacing.xs,
  },
  heroGenres: {
    color:        Colors.textSecondary,
    fontSize:     FontSize.sm,
    marginBottom: Spacing.md,
  },
  heroActions: {
    flexDirection: 'row',
    gap:           Spacing.sm,
    alignItems:    'center',
  },
  heroBtn: {
    flexDirection:    'row',
    alignItems:       'center',
    gap:              Spacing.xs,
    backgroundColor:  Colors.primary,
    paddingHorizontal: Spacing.lg,
    paddingVertical:  Spacing.sm + 2,
    borderRadius:     Radius.full,
  },
  heroBtnText: {
    color:      Colors.text,
    fontSize:   FontSize.md,
    fontWeight: '700',
  },
  heroBtnSecondary: {
    flexDirection:    'row',
    alignItems:       'center',
    gap:              Spacing.xs,
    backgroundColor:  'rgba(255,255,255,0.15)',
    paddingHorizontal: Spacing.lg,
    paddingVertical:  Spacing.sm + 2,
    borderRadius:     Radius.full,
    borderWidth:      1,
    borderColor:      'rgba(255,255,255,0.2)',
  },
  heroBtnSecondaryText: {
    color:      Colors.textSecondary,
    fontSize:   FontSize.md,
    fontWeight: '600',
  },
  heroDots: {
    position:      'absolute',
    bottom:        Spacing.md,
    right:         Spacing.lg,
    flexDirection: 'row',
    gap:           5,
  },
  dot: {
    width:           6,
    height:          6,
    borderRadius:    Radius.full,
    backgroundColor: Colors.textMuted,
  },
  dotActive: {
    backgroundColor: Colors.primary,
    width:           18,
  },

  // ── Sections ──
  section: {
    marginBottom: Spacing.xl,
  },
  sectionHeader: {
    flexDirection:    'row',
    alignItems:       'center',
    justifyContent:   'space-between',
    paddingHorizontal: Spacing.lg,
    marginBottom:     Spacing.md,
  },
  sectionTitleRow: {
    flexDirection: 'row',
    alignItems:    'center',
    gap:           Spacing.xs,
  },
  sectionTitle: {
    color:      Colors.text,
    fontSize:   FontSize.lg,
    fontWeight: '700',
  },
  countChip: {
    backgroundColor: Colors.primary + '33',
    borderRadius:    Radius.full,
    paddingHorizontal: 8,
    paddingVertical:   2,
    borderWidth:       1,
    borderColor:       Colors.primary + '55',
  },
  countChipText: {
    color:      Colors.primary,
    fontSize:   FontSize.xs,
    fontWeight: '700',
  },
  seeAll: {
    color:      Colors.primary,
    fontSize:   FontSize.sm,
    fontWeight: '600',
  },
  hList: {
    paddingHorizontal: Spacing.lg,
    gap:               Spacing.sm,
  },

  // ── Grille complète ──
  gridSection: {
    marginBottom: Spacing.xxl,
  },
  grid: {
    flexDirection: 'row',
    flexWrap:      'wrap',
    paddingHorizontal: Spacing.md,
    gap:               Spacing.md,
  },
});
