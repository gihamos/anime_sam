import React from 'react';
import { View, Text, StyleSheet, Pressable, Dimensions } from 'react-native';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Radius, FontSize, Spacing } from '@/constants/colors';
import { CatalogueSummary } from '@/types';
import { useIsFavori, useToggleFavori } from '@/hooks/useFavorites';
import { useAuthStore } from '@/stores/authStore';
import ScoreBadge from './ScoreBadge';

const CARD_WIDTH = (Dimensions.get('window').width - Spacing.md * 3) / 2;

interface Props {
  item: CatalogueSummary;
  width?: number;
  showFavori?: boolean;
  // Légende affichée sous le titre — utilisée par les lignes "Recommandé pour vous" /
  // "Titres similaires" pour expliquer pourquoi ce titre est proposé.
  reason?: string;
}

function FavoriButton({ slug }: { slug: string }) {
  const isFavori = useIsFavori(slug);
  const toggle = useToggleFavori(slug);

  return (
    <Pressable
      style={fav.btn}
      onPress={(e) => { e.stopPropagation(); toggle.mutate(); }}
      hitSlop={8}
    >
      <Ionicons
        name={isFavori ? 'heart' : 'heart-outline'}
        size={18}
        color={isFavori ? Colors.error : Colors.text}
      />
    </Pressable>
  );
}

export default function AnimeCard({ item, width = CARD_WIDTH, showFavori = true, reason }: Props) {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  const stateColor =
    item.etat === 'termine'
      ? Colors.success
      : item.etat === 'en_cours'
      ? Colors.warning
      : Colors.textMuted;

  const imageUri = item.enrichment?.cover_url || item.image || 'https://via.placeholder.com/200x280';

  return (
    <Pressable
      style={[styles.card, { width }]}
      onPress={() => router.push(`/anime/${item.slug}`)}
    >
      <View style={styles.imageContainer}>
        <Image
          source={{ uri: imageUri }}
          style={styles.image}
          contentFit="cover"
          transition={300}
        />
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.85)']}
          style={styles.gradient}
        />
        {item.etat && (
          <View style={[styles.stateBadge, { backgroundColor: stateColor + '33', borderColor: stateColor }]}>
            <View style={[styles.stateDot, { backgroundColor: stateColor }]} />
          </View>
        )}
        {item.langue && (
          <View style={styles.langBadge}>
            <Text style={styles.langText}>{item.langue.toUpperCase()}</Text>
          </View>
        )}
        <View style={styles.scoreBadgeWrap}>
          <ScoreBadge enrichment={item.enrichment} note={item.note} />
        </View>
        {item.in_db === false && (
          <View style={styles.notInDbBadge}>
            <Ionicons name="cloud-offline-outline" size={11} color={Colors.text} />
            <Text style={styles.notInDbText}>Pas en base</Text>
          </View>
        )}
        {isAuthenticated && showFavori && (
          <FavoriButton slug={item.slug} />
        )}
      </View>
      <View style={styles.info}>
        <Text style={styles.title} numberOfLines={2}>{item.nom}</Text>
        {reason ? (
          <Text style={styles.reason} numberOfLines={1}>{reason}</Text>
        ) : (
          item.annee && <Text style={styles.year}>{item.annee}</Text>
        )}
      </View>
    </Pressable>
  );
}

const fav = StyleSheet.create({
  btn: {
    position: 'absolute',
    top: Spacing.xs,
    left: Spacing.xs,
    width: 30,
    height: 30,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

const styles = StyleSheet.create({
  card: {
    borderRadius: Radius.md,
    overflow: 'hidden',
    backgroundColor: Colors.card,
    marginBottom: Spacing.md,
  },
  imageContainer: {
    aspectRatio: 2 / 3,
    position: 'relative',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  gradient: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '40%',
  },
  stateBadge: {
    position: 'absolute',
    top: Spacing.xs,
    right: Spacing.xs,
    width: 12,
    height: 12,
    borderRadius: Radius.full,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stateDot: {
    width: 6,
    height: 6,
    borderRadius: Radius.full,
  },
  langBadge: {
    position: 'absolute',
    bottom: Spacing.xs,
    left: Spacing.xs,
    backgroundColor: Colors.primary + 'cc',
    paddingHorizontal: Spacing.xs,
    paddingVertical: 2,
    borderRadius: Radius.sm,
  },
  langText: {
    color: Colors.text,
    fontSize: FontSize.xs,
    fontWeight: '700',
  },
  scoreBadgeWrap: {
    position: 'absolute',
    bottom: Spacing.xs,
    right: Spacing.xs,
  },
  notInDbBadge: {
    position: 'absolute',
    top: Spacing.xs,
    right: Spacing.xs,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: Colors.overlay,
    borderRadius: Radius.sm,
    paddingHorizontal: 6,
    paddingVertical: 3,
  },
  notInDbText: {
    color: Colors.text,
    fontSize: 9,
    fontWeight: '700',
  },
  info: {
    padding: Spacing.sm,
  },
  title: {
    color: Colors.text,
    fontSize: FontSize.sm,
    fontWeight: '600',
    lineHeight: 18,
  },
  year: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    marginTop: 2,
  },
  reason: {
    color: Colors.primaryLight,
    fontSize: FontSize.xs,
    marginTop: 2,
    fontStyle: 'italic',
  },
});
