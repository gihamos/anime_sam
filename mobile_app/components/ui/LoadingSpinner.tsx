import React from 'react';
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native';
import { Colors, FontSize } from '@/constants/colors';

interface Props {
  size?: 'small' | 'large';
  message?: string;
  fullScreen?: boolean;
}

export default function LoadingSpinner({ size = 'large', message, fullScreen = false }: Props) {
  return (
    <View style={[styles.container, fullScreen && styles.fullScreen]}>
      <ActivityIndicator size={size} color={Colors.primary} />
      {message && <Text style={styles.message}>{message}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
    gap: 12,
  },
  fullScreen: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  message: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
});
