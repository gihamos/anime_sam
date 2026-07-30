import React, { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ScrollView,
  Pressable,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useAuthStore } from '@/stores/authStore';
import { useDownloadStore } from '@/stores/downloadStore';
import { usePlayerStore } from '@/stores/playerStore';
import { useScanReaderStore } from '@/stores/scanReaderStore';
import { deleteLocalFile, deleteLocalScanChapter, formatSpeed, formatEta } from '@/hooks/useDownloads';
import { downloadApi } from '@/services/api';
import { ActiveJob, LocalFile, LocalScanChapter } from '@/types';

// ─── Active job card ──────────────────────────────────────────────────────────

function JobCard({ job }: { job: ActiveJob }) {
  const { removeJob } = useDownloadStore();

  const handleCancel = () => {
    Alert.alert('Annuler', `Annuler le téléchargement de "${job.label}" ?`, [
      { text: 'Non', style: 'cancel' },
      {
        text: 'Oui', style: 'destructive',
        onPress: async () => {
          try { await downloadApi.cancel(job.job_id); } catch {}
          removeJob(job.job_id);
        },
      },
    ]);
  };

  const statusColor = {
    pending:     Colors.textMuted,
    downloading: Colors.primary,
    ready:       Colors.success,
    error:       Colors.error,
  }[job.status] ?? Colors.textMuted;

  const statusLabel = {
    pending:     'En attente…',
    downloading: job.job_type === 'scan' ? 'Téléchargement pages…' : 'Téléchargement…',
    ready:       'Finalisation…',
    error:       'Erreur',
  }[job.status] ?? job.status;

  const pct = Math.round(job.progress ?? 0);

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Ionicons
          name={job.job_type === 'scan' ? 'book-outline' : 'film-outline'}
          size={16}
          color={Colors.textMuted}
          style={{ marginRight: Spacing.xs, marginTop: 2 }}
        />
        <View style={{ flex: 1 }}>
          <Text style={styles.cardTitle} numberOfLines={2}>{job.label}</Text>
          <Text style={styles.cardMeta}>{job.catalogue_nom}</Text>
        </View>
        <Pressable style={styles.cancelBtn} onPress={handleCancel}>
          <Ionicons name="close-circle" size={22} color={Colors.textMuted} />
        </Pressable>
      </View>

      <View style={styles.progressBg}>
        <View style={[styles.progressFill, { width: `${pct}%`, backgroundColor: statusColor }]} />
      </View>

      <View style={styles.statusRow}>
        <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
        <Text style={styles.pctText}>{pct}%</Text>
      </View>

      {job.status === 'downloading' && job.job_type !== 'scan' && (
        <View style={styles.statsRow}>
          {job.dl_speed > 0 && <Text style={styles.stat}>{formatSpeed(job.dl_speed)}</Text>}
          {job.dl_eta > 0   && <Text style={styles.stat}>⏱ {formatEta(job.dl_eta)}</Text>}
          {job.nb_items > 1 && <Text style={styles.stat}>{job.nb_items} fichiers</Text>}
        </View>
      )}

      {job.status === 'downloading' && job.job_type === 'scan' && job.nb_items > 0 && (
        <Text style={styles.stat}>
          {Math.round(pct * job.nb_items / 100)}/{job.nb_items} pages
        </Text>
      )}

      {job.status === 'error' && job.error && (
        <Text style={styles.errorText} numberOfLines={2}>{job.error}</Text>
      )}
    </View>
  );
}

// ─── Local video/film file card ───────────────────────────────────────────────

function LocalFileCard({ file }: { file: LocalFile }) {
  const router = useRouter();
  const { removeLocalFile } = useDownloadStore();
  const setVideo = usePlayerStore((s) => s.setVideo);

  const handleDelete = () => {
    Alert.alert('Supprimer', `Supprimer "${file.label}" de l'appareil ?`, [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer', style: 'destructive',
        onPress: () => deleteLocalFile(file, removeLocalFile),
      },
    ]);
  };

  const handlePlay = () => {
    if (file.is_single) {
      setVideo({ url: file.local_uri, player: 'local', title: file.label });
      router.push('/player');
    } else {
      Alert.alert(
        'Archive ZIP',
        'Ce contenu est un fichier ZIP contenant plusieurs épisodes. Extrayez-le pour lire les épisodes individuellement.'
      );
    }
  };

  const sizeMb  = (file.size_bytes / 1024 / 1024).toFixed(1);
  const dateStr = new Date(file.downloaded_at).toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Ionicons
          name={file.is_single ? 'film' : 'archive'}
          size={22}
          color={Colors.primary}
          style={{ marginRight: Spacing.sm }}
        />
        <View style={{ flex: 1 }}>
          <Text style={styles.cardTitle} numberOfLines={2}>{file.label}</Text>
          <Text style={styles.cardMeta}>{file.catalogue_nom}</Text>
        </View>
      </View>

      <View style={styles.fileMetaRow}>
        <Text style={styles.fileMeta}>{sizeMb} Mo</Text>
        <Text style={styles.fileMeta}>·</Text>
        <Text style={styles.fileMeta}>{dateStr}</Text>
        {!file.is_single && (
          <Text style={[styles.fileMeta, { color: Colors.warning }]}>ZIP</Text>
        )}
      </View>

      <View style={styles.fileActions}>
        {file.is_single && (
          <Pressable style={styles.playBtn} onPress={handlePlay}>
            <Ionicons name="play" size={14} color={Colors.text} />
            <Text style={styles.playBtnText}>Lire hors ligne</Text>
          </Pressable>
        )}
        <Pressable style={styles.deleteBtn} onPress={handleDelete}>
          <Ionicons name="trash-outline" size={14} color={Colors.error} />
          <Text style={styles.deleteBtnText}>Supprimer</Text>
        </Pressable>
      </View>
    </View>
  );
}

// ─── Local scan chapter card ──────────────────────────────────────────────────

function ScanChapterCard({ chapter }: { chapter: LocalScanChapter }) {
  const router = useRouter();
  const { removeScanChapter } = useDownloadStore();
  const setScanChapitre = useScanReaderStore((s) => s.setChapitre);

  const handleDelete = () => {
    Alert.alert(
      'Supprimer',
      `Supprimer le chapitre ${chapter.chapitre_num} de "${chapter.catalogue_nom}" ?`,
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Supprimer', style: 'destructive',
          onPress: () => deleteLocalScanChapter(chapter, removeScanChapter),
        },
      ]
    );
  };

  const handleRead = () => {
    const chapitre = {
      numero:   chapter.chapitre_num,
      titre:    chapter.chapitre_titre,
      url:      '',
      lecteurs: [],
      images:   chapter.local_pages.filter(Boolean),
    };
    setScanChapitre({
      chapitre,
      chapitres:     [chapitre],
      chapitreIndex: 0,
      catalogueNom:  chapter.catalogue_nom,
      catalogueSlug: chapter.slug,
      scanNom:       chapter.scan_nom,
      scanSlug:      chapter.scan_slug,
    });
    router.push('/scan-reader');
  };

  const sizeMb  = (chapter.size_bytes / 1024 / 1024).toFixed(1);
  const dateStr = new Date(chapter.downloaded_at).toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Ionicons name="book" size={22} color={Colors.vostfr} style={{ marginRight: Spacing.sm }} />
        <View style={{ flex: 1 }}>
          <Text style={styles.cardTitle} numberOfLines={1}>
            {chapter.catalogue_nom} · Ch. {chapter.chapitre_num}
            {chapter.chapitre_titre ? ` — ${chapter.chapitre_titre}` : ''}
          </Text>
          <Text style={styles.cardMeta}>{chapter.scan_nom}</Text>
        </View>
      </View>

      <View style={styles.fileMetaRow}>
        <Text style={styles.fileMeta}>{chapter.page_count} pages</Text>
        <Text style={styles.fileMeta}>·</Text>
        <Text style={styles.fileMeta}>{sizeMb} Mo</Text>
        <Text style={styles.fileMeta}>·</Text>
        <Text style={styles.fileMeta}>{dateStr}</Text>
      </View>

      <View style={styles.fileActions}>
        <Pressable style={styles.playBtn} onPress={handleRead}>
          <Ionicons name="book-outline" size={14} color={Colors.text} />
          <Text style={styles.playBtnText}>Lire hors ligne</Text>
        </Pressable>
        <Pressable style={styles.deleteBtn} onPress={handleDelete}>
          <Ionicons name="trash-outline" size={14} color={Colors.error} />
          <Text style={styles.deleteBtnText}>Supprimer</Text>
        </Pressable>
      </View>
    </View>
  );
}

// ─── Groupement par catalogue → saison/scan ───────────────────────────────────

interface VideoGroup {
  catalogueNom: string;
  subGroups: { title: string; files: LocalFile[] }[];
}

function groupLocalFiles(files: LocalFile[]): VideoGroup[] {
  const byCatalogue = new Map<string, LocalFile[]>();
  for (const f of files) {
    byCatalogue.set(f.catalogue_nom, [...(byCatalogue.get(f.catalogue_nom) ?? []), f]);
  }
  return Array.from(byCatalogue.entries()).map(([catalogueNom, catFiles]) => {
    // label = "Saison X · Ép. N" pour les épisodes, ou juste le nom du film (pas de ' · ')
    const bySub = new Map<string, LocalFile[]>();
    for (const f of catFiles) {
      const title = f.label.includes(' · ') ? f.label.split(' · ')[0] : 'Films';
      bySub.set(title, [...(bySub.get(title) ?? []), f]);
    }
    return { catalogueNom, subGroups: Array.from(bySub.entries()).map(([title, files]) => ({ title, files })) };
  });
}

interface ScanGroup {
  catalogueNom: string;
  subGroups: { title: string; chapters: LocalScanChapter[] }[];
}

function groupScanChapters(chapters: LocalScanChapter[]): ScanGroup[] {
  const byCatalogue = new Map<string, LocalScanChapter[]>();
  for (const c of chapters) {
    byCatalogue.set(c.catalogue_nom, [...(byCatalogue.get(c.catalogue_nom) ?? []), c]);
  }
  return Array.from(byCatalogue.entries()).map(([catalogueNom, catChapters]) => {
    const bySub = new Map<string, LocalScanChapter[]>();
    for (const c of catChapters) {
      bySub.set(c.scan_nom, [...(bySub.get(c.scan_nom) ?? []), c]);
    }
    return { catalogueNom, subGroups: Array.from(bySub.entries()).map(([title, chapters]) => ({ title, chapters })) };
  });
}

function CatalogueSection({
  catalogueNom, count, expanded, onToggle, children,
}: {
  catalogueNom: string; count: number; expanded: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <View style={grp.container}>
      <Pressable style={grp.header} onPress={onToggle}>
        <Ionicons name={expanded ? 'chevron-down' : 'chevron-forward'} size={16} color={Colors.textMuted} />
        <Text style={grp.title} numberOfLines={1}>{catalogueNom}</Text>
        <View style={grp.countChip}>
          <Text style={grp.countText}>{count}</Text>
        </View>
      </Pressable>
      {expanded && <View style={grp.body}>{children}</View>}
    </View>
  );
}

function useToggleSet() {
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());
  const toggle = (key: string) => setExpanded((prev) => {
    const next = new Set(prev);
    next.has(key) ? next.delete(key) : next.add(key);
    return next;
  });
  return { expanded, toggle };
}

// ─── Main screen ─────────────────────────────────────────────────────────────

export default function DownloadsScreen() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const { jobs, localFiles, scanChapters, loadFromStorage } = useDownloadStore();
  const [section, setSection] = React.useState<'active' | 'local' | 'scans'>('active');
  const videoGroups = useMemo(() => groupLocalFiles(localFiles), [localFiles]);
  const scanGroups   = useMemo(() => groupScanChapters(scanChapters), [scanChapters]);
  const videoToggle  = useToggleSet();
  const scanToggle   = useToggleSet();

  useEffect(() => { loadFromStorage(); }, []);

  if (!isAuthenticated) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.empty}>
          <Ionicons name="lock-closed-outline" size={56} color={Colors.textMuted} />
          <Text style={styles.emptyTitle}>Connexion requise</Text>
          <Text style={styles.emptySubtitle}>
            Connectez-vous pour accéder à vos téléchargements.
          </Text>
          <Pressable style={styles.loginBtn} onPress={() => router.push('/(tabs)/profile')}>
            <Text style={styles.loginBtnText}>Se connecter</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const activeJobs  = jobs.filter((j) => j.status !== 'error');
  const errorJobs   = jobs.filter((j) => j.status === 'error');
  const displayJobs = [...activeJobs, ...errorJobs];
  const activeCount = activeJobs.length;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Téléchargements</Text>
        {activeCount > 0 && (
          <ActivityIndicator size="small" color={Colors.primary} style={{ marginLeft: Spacing.sm }} />
        )}
      </View>

      {/* Segmented control — 3 onglets */}
      <View style={styles.segmented}>
        <Pressable
          style={[styles.segment, section === 'active' && styles.segmentActive]}
          onPress={() => setSection('active')}
        >
          <Text style={[styles.segmentText, section === 'active' && styles.segmentTextActive]}>
            En cours{activeCount > 0 ? ` (${activeCount})` : ''}
          </Text>
        </Pressable>
        <Pressable
          style={[styles.segment, section === 'local' && styles.segmentActive]}
          onPress={() => setSection('local')}
        >
          <Text style={[styles.segmentText, section === 'local' && styles.segmentTextActive]}>
            Vidéos{localFiles.length > 0 ? ` (${localFiles.length})` : ''}
          </Text>
        </Pressable>
        <Pressable
          style={[styles.segment, section === 'scans' && styles.segmentActive]}
          onPress={() => setSection('scans')}
        >
          <Text style={[styles.segmentText, section === 'scans' && styles.segmentTextActive]}>
            Scans{scanChapters.length > 0 ? ` (${scanChapters.length})` : ''}
          </Text>
        </Pressable>
      </View>

      {section === 'active' && (
        <FlatList
          data={displayJobs}
          keyExtractor={(j) => j.job_id}
          renderItem={({ item }) => <JobCard job={item} />}
          contentContainerStyle={displayJobs.length === 0 ? { flex: 1 } : styles.list}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="download-outline" size={56} color={Colors.textMuted} />
              <Text style={styles.emptyTitle}>Aucun téléchargement actif</Text>
              <Text style={styles.emptySubtitle}>
                Ouvrez un anime ou un manga et appuyez sur Télécharger pour démarrer.
              </Text>
            </View>
          }
        />
      )}

      {section === 'local' && (
        localFiles.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="film-outline" size={56} color={Colors.textMuted} />
            <Text style={styles.emptyTitle}>Aucune vidéo hors ligne</Text>
            <Text style={styles.emptySubtitle}>
              Les épisodes et films téléchargés apparaîtront ici.
            </Text>
          </View>
        ) : (
          <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
            {videoGroups.map((group) => (
              <CatalogueSection
                key={group.catalogueNom}
                catalogueNom={group.catalogueNom}
                count={group.subGroups.reduce((sum, g) => sum + g.files.length, 0)}
                expanded={videoToggle.expanded.has(group.catalogueNom)}
                onToggle={() => videoToggle.toggle(group.catalogueNom)}
              >
                {group.subGroups.map((sub) => (
                  <View key={sub.title} style={grp.subGroup}>
                    <Text style={grp.subTitle}>{sub.title}</Text>
                    {sub.files.map((f) => <LocalFileCard key={f.id} file={f} />)}
                  </View>
                ))}
              </CatalogueSection>
            ))}
          </ScrollView>
        )
      )}

      {section === 'scans' && (
        scanChapters.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="book-outline" size={56} color={Colors.textMuted} />
            <Text style={styles.emptyTitle}>Aucun scan hors ligne</Text>
            <Text style={styles.emptySubtitle}>
              Ouvrez un manga et appuyez sur{' '}
              <Ionicons name="download-outline" size={13} color={Colors.textMuted} />
              {' '}sur un chapitre pour le télécharger.
            </Text>
          </View>
        ) : (
          <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
            {scanGroups.map((group) => (
              <CatalogueSection
                key={group.catalogueNom}
                catalogueNom={group.catalogueNom}
                count={group.subGroups.reduce((sum, g) => sum + g.chapters.length, 0)}
                expanded={scanToggle.expanded.has(group.catalogueNom)}
                onToggle={() => scanToggle.toggle(group.catalogueNom)}
              >
                {group.subGroups.map((sub) => (
                  <View key={sub.title} style={grp.subGroup}>
                    <Text style={grp.subTitle}>{sub.title}</Text>
                    {sub.chapters
                      .sort((a, b) => a.chapitre_num - b.chapitre_num)
                      .map((c) => <ScanChapterCard key={c.id} chapter={c} />)}
                  </View>
                ))}
              </CatalogueSection>
            ))}
          </ScrollView>
        )
      )}
    </SafeAreaView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },

  header: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.sm,
  },
  headerTitle: { color: Colors.text, fontSize: FontSize.xxl, fontWeight: '800' },

  segmented: {
    flexDirection: 'row', marginHorizontal: Spacing.lg, marginBottom: Spacing.md,
    backgroundColor: Colors.surfaceAlt, borderRadius: Radius.md, padding: 3,
  },
  segment:           { flex: 1, paddingVertical: Spacing.sm, alignItems: 'center', borderRadius: Radius.sm },
  segmentActive:     { backgroundColor: Colors.primary },
  segmentText:       { color: Colors.textMuted, fontSize: FontSize.xs, fontWeight: '600' },
  segmentTextActive: { color: Colors.text },

  list: { paddingHorizontal: Spacing.lg, paddingBottom: 100, gap: Spacing.md },

  card: {
    backgroundColor: Colors.card, borderRadius: Radius.lg,
    padding: Spacing.md, borderWidth: 1, borderColor: Colors.border,
  },
  cardHeader:  { flexDirection: 'row', alignItems: 'flex-start', marginBottom: Spacing.sm },
  cardTitle:   { color: Colors.text, fontSize: FontSize.md, fontWeight: '700', lineHeight: 20 },
  cardMeta:    { color: Colors.textMuted, fontSize: FontSize.xs, marginTop: 2 },
  cancelBtn:   { padding: 4, marginLeft: Spacing.sm },

  progressBg:   { height: 4, backgroundColor: Colors.border, borderRadius: 2, marginBottom: Spacing.sm, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 2 },

  statusRow:  { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  statusText: { fontSize: FontSize.xs, fontWeight: '600' },
  pctText:    { color: Colors.textSecondary, fontSize: FontSize.xs },

  statsRow: { flexDirection: 'row', gap: Spacing.md, marginTop: Spacing.xs },
  stat:     { color: Colors.textMuted, fontSize: FontSize.xs, marginTop: Spacing.xs },
  errorText: { color: Colors.error, fontSize: FontSize.xs, marginTop: Spacing.sm },

  fileMetaRow: { flexDirection: 'row', gap: Spacing.sm, alignItems: 'center', marginBottom: Spacing.sm },
  fileMeta:    { color: Colors.textMuted, fontSize: FontSize.xs },

  fileActions: { flexDirection: 'row', gap: Spacing.sm },
  playBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.xs, backgroundColor: Colors.primary,
    borderRadius: Radius.sm, paddingVertical: Spacing.sm,
  },
  playBtnText:  { color: Colors.text, fontSize: FontSize.xs, fontWeight: '700' },
  deleteBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.xs, backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.sm, paddingVertical: Spacing.sm, paddingHorizontal: Spacing.md,
    borderWidth: 1, borderColor: Colors.error + '55',
  },
  deleteBtnText: { color: Colors.error, fontSize: FontSize.xs, fontWeight: '700' },

  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: Spacing.md, padding: Spacing.xl },
  emptyTitle:    { color: Colors.text, fontSize: FontSize.xl, fontWeight: '700', textAlign: 'center' },
  emptySubtitle: { color: Colors.textMuted, fontSize: FontSize.md, textAlign: 'center', lineHeight: 22 },
  loginBtn: {
    backgroundColor: Colors.primary, borderRadius: Radius.full,
    paddingVertical: Spacing.md, paddingHorizontal: Spacing.xl, marginTop: Spacing.sm,
  },
  loginBtnText: { color: Colors.text, fontSize: FontSize.md, fontWeight: '700' },
});

const grp = StyleSheet.create({
  container: {
    marginBottom: Spacing.md, backgroundColor: Colors.surfaceAlt, borderRadius: Radius.lg,
    borderWidth: 1, borderColor: Colors.border, overflow: 'hidden',
  },
  header: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    padding: Spacing.md,
  },
  title: { flex: 1, color: Colors.text, fontSize: FontSize.md, fontWeight: '700' },
  countChip: {
    backgroundColor: Colors.primary + '33', borderRadius: Radius.full,
    paddingHorizontal: 8, paddingVertical: 2,
    borderWidth: 1, borderColor: Colors.primary + '55',
  },
  countText: { color: Colors.primary, fontSize: FontSize.xs, fontWeight: '700' },
  body: { paddingHorizontal: Spacing.md, paddingBottom: Spacing.md, gap: Spacing.md },
  subGroup: { gap: Spacing.sm },
  subTitle: { color: Colors.textMuted, fontSize: FontSize.sm, fontWeight: '600' },
});
