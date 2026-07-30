import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import SearchBar from '@/components/ui/SearchBar';
import AnimeCard from '@/components/ui/AnimeCard';
import FilterSheet from '@/components/ui/FilterSheet';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { useCatalogueSearch } from '@/hooks/useAnime';
import { SearchFilters } from '@/types';

export default function SearchScreen() {
  const params = useLocalSearchParams<{ type?: string; etat?: string }>();

  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>(() => ({
    type: params.type,
    etat: params.etat,
  }));
  const [showFilters, setShowFilters] = useState(false);

  // Ré-appliquer les filtres quand on arrive depuis la page d'accueil
  useEffect(() => {
    if (params.type !== undefined || params.etat !== undefined) {
      setFilters({ type: params.type, etat: params.etat });
      setQuery('');
    }
  }, [params.type, params.etat]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 500);
    return () => clearTimeout(timer);
  }, [query]);

  // Recherche unique : la DB et le site anime-sama.to sont combinés côté serveur
  // (voir GET /catalogues/rechercher) — chaque résultat porte `in_db` pour indiquer
  // s'il est déjà synchronisé en base ou trouvé seulement en direct sur le site.
  const search = useCatalogueSearch({ ...filters, q: debouncedQuery, limit: 50 }, true);

  const results = search.data ?? [];
  const isLoading = search.isLoading;
  const total = search.data?.length;

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  const contextTitle = params.type === 'film' ? 'Films'
    : params.type === 'scan' ? 'Scans & Manga'
    : params.type === 'anime' ? 'Animés'
    : params.etat === 'en_cours' ? 'En cours de diffusion'
    : null;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>{contextTitle ?? 'Recherche'}</Text>
        <View style={styles.searchRow}>
          <View style={styles.searchBarWrapper}>
            <SearchBar
              value={query}
              onChangeText={setQuery}
              onSubmit={() => {}}
            />
          </View>
          <Pressable
            style={[styles.filterBtn, activeFilterCount > 0 && styles.filterBtnActive]}
            onPress={() => setShowFilters(true)}
          >
            <Ionicons name="options" size={20} color={activeFilterCount > 0 ? Colors.text : Colors.textMuted} />
            {activeFilterCount > 0 && (
              <View style={styles.filterBadge}>
                <Text style={styles.filterBadgeText}>{activeFilterCount}</Text>
              </View>
            )}
          </Pressable>
        </View>
      </View>

      {isLoading ? (
        <LoadingSpinner message="Recherche en cours..." />
      ) : (
        <FlatList
          data={results}
          keyExtractor={(item) => item.slug}
          numColumns={2}
          contentContainerStyle={styles.list}
          columnWrapperStyle={styles.row}
          ListHeaderComponent={
            total !== undefined && debouncedQuery
              ? () => (
                  <Text style={styles.resultCount}>
                    {total} résultat{total !== 1 ? 's' : ''}
                  </Text>
                )
              : null
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="search-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyText}>
                {debouncedQuery || activeFilterCount > 0
                  ? 'Aucun résultat trouvé'
                  : 'Recherchez un anime, film ou scan'}
              </Text>
            </View>
          }
          renderItem={({ item }) => <AnimeCard item={item} />}
        />
      )}

      <FilterSheet
        visible={showFilters}
        onClose={() => setShowFilters(false)}
        filters={filters}
        onChange={setFilters}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.sm,
    gap: Spacing.md,
  },
  title: {
    color: Colors.text,
    fontSize: FontSize.xxl,
    fontWeight: '800',
  },
  searchRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
    alignItems: 'center',
  },
  searchBarWrapper: {
    flex: 1,
  },
  filterBtn: {
    width: 44,
    height: 44,
    borderRadius: Radius.md,
    backgroundColor: Colors.surfaceAlt,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  filterBtnActive: {
    backgroundColor: Colors.primary + '33',
    borderWidth: 1,
    borderColor: Colors.primary,
  },
  filterBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 16,
    height: 16,
    borderRadius: Radius.full,
    backgroundColor: Colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  filterBadgeText: {
    color: Colors.text,
    fontSize: 9,
    fontWeight: '700',
  },
  list: {
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.sm,
    paddingBottom: Spacing.xxl,
  },
  row: {
    gap: Spacing.md,
  },
  resultCount: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    paddingVertical: Spacing.sm,
  },
  empty: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: Spacing.xxl * 2,
    gap: Spacing.md,
  },
  emptyText: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
    textAlign: 'center',
  },
});
