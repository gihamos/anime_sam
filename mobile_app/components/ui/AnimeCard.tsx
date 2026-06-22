import React from 'react';
import { View, Text, StyleSheet, Pressable, Dimensions } from 'react-native';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Colors, Radius, FontSize, Spacing } from '@/constants/colors';
import { CatalogueSummary } from '@/types';

const CARD_WIDTH = (Dimensions.get('window').width - Spacing.md * 3) / 2;

interface Props {
  item: CatalogueSummary;
  width?: number;
}

export default function AnimeCard({ item, width = CARD_WIDTH }: Props) {
  const router = useRouter();

  const stateColor =
    item.etat === 'termine'
      ? Colors.success
      : item.etat === 'en_cours'
      ? Colors.warning
      : Colors.textMuted;

  return (
    <Pressable
      style={[styles.card, { width }]}
      onPress={() => router.push(`/anime/${item.slug}`)}
    >
      <View style={styles.imageContainer}>
        <Image
          source={{ uri: item.image || 'https://via.placeholder.com/200x280' }}
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
      </View>
      <View style={styles.info}>
        <Text style={styles.title} numberOfLines={2}>{item.nom}</Text>
        {item.annee && <Text style={styles.year}>{item.annee}</Text>}
      </View>
    </Pressable>
  );
}

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
});
