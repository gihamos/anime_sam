import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { Colors, Radius, FontSize, Spacing } from '@/constants/colors';

interface Props {
  label: string;
  variant?: 'default' | 'outline';
}

export default function TagChip({ label, variant = 'default' }: Props) {
  return (
    <Text style={[styles.chip, variant === 'outline' && styles.outline]}>{label}</Text>
  );
}

const styles = StyleSheet.create({
  chip: {
    color: Colors.textSecondary,
    fontSize: FontSize.xs,
    fontWeight: '600',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.sm,
    overflow: 'hidden',
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: Colors.border,
  },
});
