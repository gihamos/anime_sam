import React, { useMemo } from 'react';
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
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useCatalogueList } from '@/hooks/useAnime';
import AnimeCard from '@/components/ui/AnimeCard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { CatalogueSummary } from '@/types';

const { width } = Dimensions.get('window');
const HERO_HEIGHT = 420;

export default function HomeScreen() {
  const router = useRouter();
  const { data: catalogues, isLoading, refetch, isRefetching } = useCatalogueList();

  const featured = useMemo(() => catalogues?.slice(0, 5) ?? [], [catalogues]);
  const recent = useMemo(() => catalogues?.slice(0, 10) ?? [], [catalogues]);
  const ongoing = useMemo(
    () => catalogues?.filter((c) => c.etat === 'en_cours').slice(0, 10) ?? [],
    [catalogues]
  );

  const [heroIndex, setHeroIndex] = React.useState(0);
  const hero = featured[heroIndex];

  if (isLoading) return <LoadingSpinner fullScreen message="Chargement du catalogue..." />;

  const HeroSection = () =>
    hero ? (
      <Pressable style={styles.hero} onPress={() => router.push(`/anime/${hero.slug}`)}>
        <Image source={{ uri: hero.image }} style={styles.heroImage} contentFit="cover" />
        <LinearGradient
          colors={['transparent', 'rgba(10,10,15,0.6)', Colors.background]}
          style={styles.heroGradient}
        />
        <View style={styles.heroContent}>
          <View style={styles.heroBadges}>
            {hero.type && (
              <View style={styles.heroBadge}>
                <Text style={styles.heroBadgeText}>{hero.type.toUpperCase()}</Text>
              </View>
            )}
            {hero.langue && (
              <View style={[styles.heroBadge, { backgroundColor: Colors.primary + '88' }]}>
                <Text style={styles.heroBadgeText}>{hero.langue.toUpperCase()}</Text>
              </View>
            )}
          </View>
          <Text style={styles.heroTitle}>{hero.nom}</Text>
          {hero.genres.length > 0 && (
            <Text style={styles.heroGenres}>{hero.genres.slice(0, 3).join(' · ')}</Text>
          )}
          <View style={styles.heroActions}>
            <Pressable
              style={styles.heroBtn}
              onPress={() => router.push(`/anime/${hero.slug}`)}
            >
              <Text style={styles.heroBtnText}>▶ Regarder</Text>
            </Pressable>
          </View>
        </View>
        <View style={styles.heroDots}>
          {featured.map((_, i) => (
            <Pressable key={i} onPress={() => setHeroIndex(i)}>
              <View style={[styles.dot, i === heroIndex && styles.dotActive]} />
            </Pressable>
          ))}
        </View>
      </Pressable>
    ) : null;

  const HorizontalRow = ({ title, items }: { title: string; items: CatalogueSummary[] }) => (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <Pressable onPress={() => router.push('/search')}>
          <Text style={styles.seeAll}>Voir tout</Text>
        </Pressable>
      </View>
      <FlatList
        data={items}
        horizontal
        showsHorizontalScrollIndicator={false}
        keyExtractor={(item) => item.slug}
        contentContainerStyle={styles.hList}
        renderItem={({ item }) => (
          <AnimeCard item={item} width={120} />
        )}
      />
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={refetch}
            tintColor={Colors.primary}
          />
        }
      >
        <View style={styles.header}>
          <Text style={styles.logo}>🎌 Anime Sama</Text>
        </View>

        <HeroSection />

        {ongoing.length > 0 && <HorizontalRow title="En cours" items={ongoing} />}
        <HorizontalRow title="Récemment ajoutés" items={recent} />

        <View style={styles.gridSection}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Tout le catalogue</Text>
          </View>
          <View style={styles.grid}>
            {(catalogues ?? []).map((item) => (
              <AnimeCard key={item.slug} item={item} />
            ))}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  logo: {
    color: Colors.text,
    fontSize: FontSize.xxl,
    fontWeight: '800',
  },
  hero: {
    height: HERO_HEIGHT,
    position: 'relative',
    marginBottom: Spacing.xl,
  },
  heroImage: {
    width: '100%',
    height: '100%',
  },
  heroGradient: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '75%',
  },
  heroContent: {
    position: 'absolute',
    bottom: Spacing.xl,
    left: Spacing.lg,
    right: Spacing.lg,
  },
  heroBadges: {
    flexDirection: 'row',
    gap: Spacing.xs,
    marginBottom: Spacing.sm,
  },
  heroBadge: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.sm,
  },
  heroBadgeText: {
    color: Colors.text,
    fontSize: FontSize.xs,
    fontWeight: '700',
  },
  heroTitle: {
    color: Colors.text,
    fontSize: FontSize.xxxl,
    fontWeight: '800',
    lineHeight: 36,
    marginBottom: Spacing.xs,
  },
  heroGenres: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    marginBottom: Spacing.md,
  },
  heroActions: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  heroBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.sm + 2,
    borderRadius: Radius.full,
  },
  heroBtnText: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: '700',
  },
  heroDots: {
    position: 'absolute',
    bottom: Spacing.lg,
    right: Spacing.lg,
    flexDirection: 'row',
    gap: Spacing.xs,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: Radius.full,
    backgroundColor: Colors.textMuted,
  },
  dotActive: {
    backgroundColor: Colors.primary,
    width: 18,
  },
  section: {
    marginBottom: Spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.md,
  },
  sectionTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: '700',
  },
  seeAll: {
    color: Colors.primary,
    fontSize: FontSize.sm,
    fontWeight: '600',
  },
  hList: {
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
  },
  gridSection: {
    marginBottom: Spacing.xl,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: Spacing.md,
    gap: Spacing.md,
  },
});
