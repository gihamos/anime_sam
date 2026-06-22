import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  Pressable,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, Radius, FontSize } from '@/constants/colors';
import { SearchFilters } from '@/types';

interface Props {
  visible: boolean;
  onClose: () => void;
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
}

const TYPES = ['anime', 'film', 'scan'];
const LANGUAGES = ['vf', 'vostfr', 'vo'];
const STATES = ['en_cours', 'termine', 'abandonne'];
const GENRES = [
  'Action', 'Aventure', 'Comédie', 'Drame', 'Fantasy', 'Horreur',
  'Mystère', 'Romance', 'Science-Fiction', 'Shonen', 'Seinen',
  'Shoujo', 'Slice of Life', 'Sport', 'Surnaturel', 'Thriller',
];

export default function FilterSheet({ visible, onClose, filters, onChange }: Props) {
  const toggle = (key: keyof SearchFilters, value: string) => {
    onChange({ ...filters, [key]: filters[key] === value ? undefined : value });
  };

  const Chip = ({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) => (
    <TouchableOpacity
      style={[styles.chip, active && styles.chipActive]}
      onPress={onPress}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </TouchableOpacity>
  );

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.chipRow}>{children}</View>
    </View>
  );

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <View style={styles.sheetHeader}>
            <Text style={styles.sheetTitle}>Filtres</Text>
            <Pressable onPress={() => onChange({})} hitSlop={8}>
              <Text style={styles.clearText}>Effacer</Text>
            </Pressable>
            <Pressable onPress={onClose} hitSlop={8}>
              <Ionicons name="close" size={22} color={Colors.text} />
            </Pressable>
          </View>

          <ScrollView showsVerticalScrollIndicator={false}>
            <Section title="Type">
              {TYPES.map((t) => (
                <Chip key={t} label={t} active={filters.type === t} onPress={() => toggle('type', t)} />
              ))}
            </Section>

            <Section title="Langue">
              {LANGUAGES.map((l) => (
                <Chip key={l} label={l.toUpperCase()} active={filters.langue === l} onPress={() => toggle('langue', l)} />
              ))}
            </Section>

            <Section title="État">
              {STATES.map((s) => (
                <Chip key={s} label={s.replace('_', ' ')} active={filters.etat === s} onPress={() => toggle('etat', s)} />
              ))}
            </Section>

            <Section title="Genre">
              {GENRES.map((g) => (
                <Chip key={g} label={g} active={filters.genre === g} onPress={() => toggle('genre', g)} />
              ))}
            </Section>
          </ScrollView>

          <Pressable style={styles.applyBtn} onPress={onClose}>
            <Text style={styles.applyText}>Appliquer</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: Colors.overlay,
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: Colors.surface,
    borderTopLeftRadius: Radius.xl,
    borderTopRightRadius: Radius.xl,
    padding: Spacing.lg,
    maxHeight: '85%',
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: Colors.border,
    borderRadius: Radius.full,
    alignSelf: 'center',
    marginBottom: Spacing.md,
  },
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.lg,
    gap: Spacing.md,
  },
  sheetTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: '700',
  },
  clearText: {
    color: Colors.primary,
    fontSize: FontSize.md,
  },
  section: {
    marginBottom: Spacing.lg,
  },
  sectionTitle: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    fontWeight: '700',
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginBottom: Spacing.sm,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  chip: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
  },
  chipActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  chipText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
  chipTextActive: {
    color: Colors.text,
    fontWeight: '600',
  },
  applyBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
    padding: Spacing.md,
    alignItems: 'center',
    marginTop: Spacing.md,
  },
  applyText: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: '700',
  },
});
