import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Radius, FontSize, Spacing } from '@/constants/colors';

interface Props {
  label: string;
  color?: string;
  size?: 'sm' | 'md';
}

export default function Badge({ label, color = Colors.primary, size = 'sm' }: Props) {
  return (
    <View style={[styles.badge, { backgroundColor: color + '22', borderColor: color + '55' }, size === 'md' && styles.md]}>
      <Text style={[styles.text, { color }, size === 'md' && styles.textMd]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.full,
    borderWidth: 1,
  },
  md: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
  },
  text: {
    fontSize: FontSize.xs,
    fontWeight: '600',
  },
  textMd: {
    fontSize: FontSize.sm,
  },
});
