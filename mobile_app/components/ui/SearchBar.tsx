import React, { useState } from 'react';
import { View, TextInput, StyleSheet, Pressable, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Radius, Spacing, FontSize } from '@/constants/colors';

interface Props {
  value: string;
  onChangeText: (text: string) => void;
  onSubmit?: () => void;
  onClear?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export default function SearchBar({
  value,
  onChangeText,
  onSubmit,
  onClear,
  placeholder = 'Rechercher un anime...',
  autoFocus = false,
}: Props) {
  return (
    <View style={styles.container}>
      <Ionicons name="search" size={18} color={Colors.textMuted} style={styles.icon} />
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        onSubmitEditing={onSubmit}
        placeholder={placeholder}
        placeholderTextColor={Colors.textMuted}
        returnKeyType="search"
        autoFocus={autoFocus}
        autoCorrect={false}
        autoCapitalize="none"
      />
      {value.length > 0 && (
        <Pressable onPress={onClear || (() => onChangeText(''))} hitSlop={8}>
          <Ionicons name="close-circle" size={18} color={Colors.textMuted} />
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm + 2,
    gap: Spacing.sm,
  },
  icon: {},
  input: {
    flex: 1,
    color: Colors.text,
    fontSize: FontSize.md,
  },
});
