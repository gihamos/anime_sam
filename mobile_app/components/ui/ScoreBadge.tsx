import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Radius, FontSize, Spacing } from '@/constants/colors';
import { Enrichment } from '@/types';

interface Props {
  enrichment?: Enrichment;
  note?: number | null; // repli sur la note scrapée (/10) si pas de score AniList
  size?: 'sm' | 'md';
}

// Score AniList (/100) préféré à la note scrapée (/10) quand disponible — toujours
// affiché normalisé sur 10 pour rester cohérent visuellement dans toute l'app.
function resolveScore(enrichment?: Enrichment, note?: number | null): number | null {
  if (enrichment?.score != null) return enrichment.score / 10;
  if (note != null && note > 0) return note;
  return null;
}

export default function ScoreBadge({ enrichment, note, size = 'sm' }: Props) {
  const score = resolveScore(enrichment, note);
  if (score == null) return null;

  const color = score >= 7.5 ? Colors.success : score >= 5.5 ? Colors.warning : Colors.textMuted;
  const small = size === 'sm';

  return (
    <View style={[styles.badge, { borderColor: color }, small ? styles.sm : styles.md]}>
      <Ionicons name="star" size={small ? 11 : 13} color={color} />
      <Text style={[styles.text, { color }, small && styles.textSm]}>{score.toFixed(1)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: Radius.full,
    borderWidth: 1,
  },
  sm: { paddingHorizontal: Spacing.xs, paddingVertical: 2 },
  md: { paddingHorizontal: Spacing.sm, paddingVertical: 4 },
  text: { fontWeight: '700', fontSize: FontSize.sm },
  textSm: { fontSize: FontSize.xs },
});
