import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { downloadApi } from '@/services/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useAuthStore } from '@/stores/authStore';
import { DownloadJob } from '@/types';
import * as Linking from 'expo-linking';

export default function DownloadsScreen() {
  const [jobs, setJobs] = useState<DownloadJob[]>([]);
  const { isAuthenticated } = useAuthStore();
  const { apiUrl } = useSettingsStore();

  const statusColor: Record<string, string> = {
    pending: Colors.warning,
    running: Colors.primary,
    completed: Colors.success,
    failed: Colors.error,
    cancelled: Colors.textMuted,
  };

  const statusIcon: Record<string, string> = {
    pending: 'time-outline',
    running: 'sync-outline',
    completed: 'checkmark-circle',
    failed: 'close-circle',
    cancelled: 'ban-outline',
  };

  const cancelJob = async (id: string) => {
    Alert.alert('Annuler', 'Annuler ce téléchargement ?', [
      { text: 'Non', style: 'cancel' },
      {
        text: 'Oui',
        style: 'destructive',
        onPress: async () => {
          try {
            await downloadApi.cancel(id);
            setJobs((prev) => prev.filter((j) => j.id !== id));
          } catch {}
        },
      },
    ]);
  };

  const downloadFile = (jobId: string) => {
    const url = downloadApi.getFileUrl(jobId, apiUrl);
    Linking.openURL(url);
  };

  if (!isAuthenticated) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.center}>
          <Ionicons name="lock-closed" size={48} color={Colors.textMuted} />
          <Text style={styles.centerTitle}>Connexion requise</Text>
          <Text style={styles.centerText}>
            Connectez-vous pour accéder aux téléchargements.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Téléchargements</Text>
      </View>

      <FlatList
        data={jobs}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="download-outline" size={64} color={Colors.textMuted} />
            <Text style={styles.emptyTitle}>Aucun téléchargement</Text>
            <Text style={styles.emptyText}>
              Lance un téléchargement depuis la page d'un anime.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <View style={styles.jobCard}>
            <View style={styles.jobHeader}>
              <View style={styles.jobInfo}>
                <Text style={styles.jobSlug}>{item.slug}</Text>
                {item.saison && (
                  <Text style={styles.jobMeta}>
                    Saison {item.saison}
                    {item.episodes && ` · ${item.episodes.length} épisode(s)`}
                  </Text>
                )}
              </View>
              <Ionicons
                name={statusIcon[item.status] as any}
                size={22}
                color={statusColor[item.status]}
              />
            </View>

            {item.status === 'running' && item.progress !== undefined && (
              <View style={styles.progressSection}>
                <View style={styles.progressBar}>
                  <View style={[styles.progressFill, { width: `${item.progress}%` }]} />
                </View>
                <View style={styles.progressInfo}>
                  <Text style={styles.progressText}>{Math.round(item.progress)}%</Text>
                  {item.speed && <Text style={styles.progressText}>{item.speed}</Text>}
                  {item.eta && <Text style={styles.progressText}>ETA: {item.eta}</Text>}
                </View>
              </View>
            )}

            {item.error && <Text style={styles.errorText}>{item.error}</Text>}

            <View style={styles.jobActions}>
              <Text style={[styles.statusText, { color: statusColor[item.status] }]}>
                {item.status}
              </Text>
              {item.status === 'completed' && (
                <Pressable style={styles.actionBtn} onPress={() => downloadFile(item.id)}>
                  <Ionicons name="cloud-download-outline" size={16} color={Colors.primary} />
                  <Text style={styles.actionBtnText}>Télécharger</Text>
                </Pressable>
              )}
              {(item.status === 'pending' || item.status === 'running') && (
                <Pressable style={styles.cancelBtn} onPress={() => cancelJob(item.id)}>
                  <Text style={styles.cancelBtnText}>Annuler</Text>
                </Pressable>
              )}
            </View>
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  title: {
    color: Colors.text,
    fontSize: FontSize.xxl,
    fontWeight: '800',
  },
  list: {
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.xxl,
  },
  empty: {
    alignItems: 'center',
    paddingTop: Spacing.xxl * 2,
    gap: Spacing.md,
  },
  emptyTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: '700',
  },
  emptyText: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
    textAlign: 'center',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.md,
    paddingHorizontal: Spacing.xl,
  },
  centerTitle: {
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: '700',
  },
  centerText: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
    textAlign: 'center',
  },
  jobCard: {
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    gap: Spacing.sm,
  },
  jobHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.sm,
  },
  jobInfo: { flex: 1 },
  jobSlug: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: '600',
  },
  jobMeta: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    marginTop: 2,
  },
  progressSection: { gap: 4 },
  progressBar: {
    height: 4,
    backgroundColor: Colors.border,
    borderRadius: Radius.full,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
  },
  progressInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  progressText: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
  },
  errorText: {
    color: Colors.error,
    fontSize: FontSize.sm,
  },
  jobActions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statusText: {
    fontSize: FontSize.sm,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Colors.primary + '22',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
  },
  actionBtnText: {
    color: Colors.primary,
    fontSize: FontSize.sm,
    fontWeight: '600',
  },
  cancelBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.error + '66',
  },
  cancelBtnText: {
    color: Colors.error,
    fontSize: FontSize.sm,
  },
});
