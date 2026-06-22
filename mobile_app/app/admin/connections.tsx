import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  ActivityIndicator,
  Alert,
  TextInput,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { adminLogsApi, AccessLog } from '@/services/api';

type TabKey = 'all' | 'auth' | 'anon';

// ─── Sous-composants ──────────────────────────────────────────────────────────

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <View style={stat.card}>
      <Text style={[stat.value, color ? { color } : {}]}>{value}</Text>
      <Text style={stat.label}>{label}</Text>
    </View>
  );
}

function LogRow({
  item,
  onBan,
  isBanned,
}: {
  item: AccessLog;
  onBan: (ip: string) => void;
  isBanned: boolean;
}) {
  const isAuth   = !!item.username;
  const status   = item.status_code;
  const statusColor =
    status < 300 ? Colors.success :
    status < 400 ? Colors.info    :
    status < 500 ? Colors.warning : Colors.error;

  const date = new Date(item.timestamp);
  const dateStr = `${date.toLocaleDateString('fr-FR')} ${date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`;

  return (
    <View style={[row.container, isBanned && row.banned]}>
      <View style={row.left}>
        {/* Utilisateur / visiteur */}
        <View style={row.userLine}>
          <Ionicons
            name={isAuth ? 'person' : 'eye-outline'}
            size={12}
            color={isAuth ? Colors.primary : Colors.textMuted}
          />
          <Text style={[row.username, !isAuth && { color: Colors.textMuted, fontStyle: 'italic' }]}>
            {item.username ?? 'Visiteur anonyme'}
          </Text>
          {isBanned && (
            <View style={row.bannedBadge}>
              <Text style={row.bannedText}>BANNI</Text>
            </View>
          )}
        </View>

        {/* IP + méthode + path */}
        <Text style={row.ip}>{item.ip}</Text>
        <View style={row.pathLine}>
          <Text style={row.method}>{item.method}</Text>
          <Text style={row.path} numberOfLines={1}>{item.path}</Text>
        </View>

        {/* Date + status */}
        <View style={row.meta}>
          <Text style={[row.status, { color: statusColor }]}>{status}</Text>
          <Text style={row.date}>{dateStr}</Text>
        </View>
      </View>

      {/* Bouton bannir */}
      {!isBanned && (
        <Pressable style={row.banBtn} onPress={() => onBan(item.ip)} hitSlop={8}>
          <Ionicons name="ban" size={16} color={Colors.error} />
        </Pressable>
      )}
    </View>
  );
}

// ─── Écran principal ──────────────────────────────────────────────────────────

export default function ConnectionsScreen() {
  const router       = useRouter();
  const queryClient  = useQueryClient();
  const [tab,        setTab]       = useState<TabKey>('all');
  const [searchIp,   setSearchIp]  = useState('');
  const [searchUser, setSearchUser] = useState('');

  const logsParams = {
    auth_only: tab === 'auth' || undefined,
    anon_only: tab === 'anon' || undefined,
    ip:        searchIp.trim()   || undefined,
    username:  searchUser.trim() || undefined,
    limit:     300,
  };

  const { data: logs = [], isLoading: logsLoading, refetch, isFetching } = useQuery({
    queryKey: ['admin-logs', tab, searchIp, searchUser],
    queryFn:  () => adminLogsApi.getLogs(logsParams),
    refetchInterval: 30_000,
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['admin-logs-stats'],
    queryFn:  adminLogsApi.getStats,
    refetchInterval: 30_000,
  });

  const { data: bannedIps = [] } = useQuery({
    queryKey: ['admin-banned-ips'],
    queryFn:  adminLogsApi.getBannedIps,
  });
  const bannedSet = new Set(bannedIps.map((b) => b.ip));

  const banMutation = useMutation({
    mutationFn: ({ ip, reason }: { ip: string; reason: string }) =>
      adminLogsApi.banIp(ip, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-banned-ips'] });
    },
  });

  const clearMutation = useMutation({
    mutationFn: adminLogsApi.clearLogs,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['admin-logs'] });
      queryClient.invalidateQueries({ queryKey: ['admin-logs-stats'] });
      Alert.alert('Logs supprimés', `${res.deleted} entrées supprimées.`);
    },
  });

  const handleBan = useCallback((ip: string) => {
    Alert.alert(
      `Bannir ${ip}`,
      'Toutes les requêtes depuis cette IP seront rejetées. Raison (optionnel) :',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Bannir sans raison',
          style: 'destructive',
          onPress: () => banMutation.mutate({ ip, reason: '' }),
        },
        {
          text: 'Abus / spam',
          style: 'destructive',
          onPress: () => banMutation.mutate({ ip, reason: 'Abus / spam' }),
        },
        {
          text: 'Accès non autorisé',
          style: 'destructive',
          onPress: () => banMutation.mutate({ ip, reason: 'Accès non autorisé' }),
        },
      ],
    );
  }, [banMutation]);

  const handleClear = () => {
    Alert.alert(
      'Vider les logs',
      'Supprimer tout l\'historique des connexions ? Cette action est irréversible.',
      [
        { text: 'Annuler', style: 'cancel' },
        { text: 'Supprimer', style: 'destructive', onPress: () => clearMutation.mutate() },
      ],
    );
  };

  const TABS: { key: TabKey; label: string }[] = [
    { key: 'all',  label: 'Tous' },
    { key: 'auth', label: 'Connectés' },
    { key: 'anon', label: 'Visiteurs' },
  ];

  return (
    <SafeAreaView style={s.container} edges={['top']}>
      {/* Header */}
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.back}>
          <Ionicons name="arrow-back" size={22} color={Colors.text} />
        </Pressable>
        <Text style={s.title}>Connexions</Text>
        <Pressable onPress={handleClear} style={s.clearBtn} disabled={clearMutation.isPending}>
          <Ionicons name="trash-outline" size={18} color={Colors.error} />
        </Pressable>
      </View>

      {/* Stats */}
      {statsLoading ? (
        <ActivityIndicator color={Colors.primary} style={{ marginVertical: Spacing.md }} />
      ) : stats ? (
        <View style={s.statsRow}>
          <StatCard label="Total"     value={stats.total}     />
          <StatCard label="IPs uniq." value={stats.unique_ips} />
          <StatCard label="Connectés" value={stats.auth_count} color={Colors.primary} />
          <StatCard label="Visiteurs" value={stats.anon_count} color={Colors.textMuted} />
        </View>
      ) : null}

      {/* Tabs */}
      <View style={s.tabs}>
        {TABS.map((t) => (
          <Pressable
            key={t.key}
            style={[s.tab, tab === t.key && s.tabActive]}
            onPress={() => setTab(t.key)}
          >
            <Text style={[s.tabText, tab === t.key && s.tabTextActive]}>{t.label}</Text>
          </Pressable>
        ))}
      </View>

      {/* Filtres recherche */}
      <View style={s.filters}>
        <TextInput
          style={s.filterInput}
          value={searchIp}
          onChangeText={setSearchIp}
          placeholder="Filtrer par IP…"
          placeholderTextColor={Colors.textMuted}
          autoCorrect={false}
          autoCapitalize="none"
          keyboardType="decimal-pad"
        />
        <TextInput
          style={s.filterInput}
          value={searchUser}
          onChangeText={setSearchUser}
          placeholder="Filtrer par utilisateur…"
          placeholderTextColor={Colors.textMuted}
          autoCorrect={false}
          autoCapitalize="none"
        />
      </View>

      {/* Liste */}
      {logsLoading ? (
        <ActivityIndicator color={Colors.primary} style={{ flex: 1 }} />
      ) : (
        <FlatList
          data={logs}
          keyExtractor={(_, i) => String(i)}
          renderItem={({ item }) => (
            <LogRow
              item={item}
              onBan={handleBan}
              isBanned={bannedSet.has(item.ip)}
            />
          )}
          contentContainerStyle={s.list}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={isFetching}
              onRefresh={refetch}
              tintColor={Colors.primary}
            />
          }
          ListEmptyComponent={
            <View style={s.empty}>
              <Ionicons name="receipt-outline" size={40} color={Colors.textMuted} />
              <Text style={s.emptyText}>Aucune connexion enregistrée</Text>
            </View>
          }
          ListFooterComponent={
            stats && stats.top_ips.length > 0 ? (
              <View style={s.topSection}>
                <Text style={s.topTitle}>Top 10 IPs</Text>
                {stats.top_ips.map((t) => (
                  <View key={t.ip} style={s.topRow}>
                    <Text style={[s.topIp, bannedSet.has(t.ip) && { color: Colors.error }]}>
                      {t.ip}{bannedSet.has(t.ip) ? '  🚫' : ''}
                    </Text>
                    <View style={s.topMeta}>
                      <Text style={s.topCount}>{t.count} req.</Text>
                      {!bannedSet.has(t.ip) && (
                        <Pressable onPress={() => handleBan(t.ip)} style={s.topBanBtn}>
                          <Ionicons name="ban" size={14} color={Colors.error} />
                        </Pressable>
                      )}
                    </View>
                  </View>
                ))}

                <Text style={[s.topTitle, { marginTop: Spacing.md }]}>Top 10 utilisateurs</Text>
                {stats.top_users.map((u) => (
                  <View key={u.username} style={s.topRow}>
                    <Text style={s.topIp}>{u.username}</Text>
                    <Text style={s.topCount}>{u.count} req.</Text>
                  </View>
                ))}
              </View>
            ) : null
          }
        />
      )}
    </SafeAreaView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderColor: Colors.border,
  },
  back:     { padding: Spacing.xs, marginRight: Spacing.sm },
  title:    { flex: 1, color: Colors.text, fontSize: FontSize.xl, fontWeight: '700' },
  clearBtn: { padding: Spacing.xs },

  statsRow: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    gap: Spacing.sm,
  },

  tabs: {
    flexDirection: 'row',
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.sm,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.full,
    padding: 3,
  },
  tab: {
    flex: 1,
    paddingVertical: 7,
    borderRadius: Radius.full,
    alignItems: 'center',
  },
  tabActive:     { backgroundColor: Colors.primary },
  tabText:       { color: Colors.textMuted, fontSize: FontSize.sm, fontWeight: '600' },
  tabTextActive: { color: Colors.text },

  filters: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.md,
    gap: Spacing.sm,
    marginBottom: Spacing.sm,
  },
  filterInput: {
    flex: 1,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 7,
    color: Colors.text,
    fontSize: FontSize.xs,
    borderWidth: 1,
    borderColor: Colors.border,
  },

  list: { paddingHorizontal: Spacing.md, paddingBottom: Spacing.xl },

  empty: { alignItems: 'center', paddingTop: Spacing.xxl, gap: Spacing.sm },
  emptyText: { color: Colors.textMuted, fontSize: FontSize.md },

  topSection: {
    marginTop: Spacing.lg,
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderColor: Colors.border,
  },
  topTitle:  { color: Colors.textSecondary, fontSize: FontSize.sm, fontWeight: '700', marginBottom: Spacing.xs },
  topRow:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 5 },
  topIp:     { color: Colors.text, fontSize: FontSize.xs, flex: 1 },
  topMeta:   { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs },
  topCount:  { color: Colors.textMuted, fontSize: FontSize.xs },
  topBanBtn: { padding: 3 },
});

// Styles des cartes stats
const stat = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    padding: Spacing.sm,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 2,
  },
  value: { color: Colors.text, fontSize: FontSize.lg, fontWeight: '800' },
  label: { color: Colors.textMuted, fontSize: 10 },
});

// Styles des lignes de log
const row = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    padding: Spacing.sm,
    marginBottom: Spacing.xs,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  banned: { borderColor: Colors.error + '55', backgroundColor: Colors.error + '0d' },
  left:   { flex: 1, gap: 3 },

  userLine:    { flexDirection: 'row', alignItems: 'center', gap: 5 },
  username:    { color: Colors.text, fontSize: FontSize.sm, fontWeight: '600', flex: 1 },
  bannedBadge: { backgroundColor: Colors.error + '33', borderRadius: Radius.sm, paddingHorizontal: 5, paddingVertical: 2 },
  bannedText:  { color: Colors.error, fontSize: 9, fontWeight: '800' },

  ip:       { color: Colors.textMuted, fontSize: FontSize.xs },
  pathLine: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  method:   { color: Colors.info, fontSize: 10, fontWeight: '700' },
  path:     { color: Colors.textSecondary, fontSize: 10, flex: 1 },

  meta:   { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  status: { fontSize: 10, fontWeight: '700' },
  date:   { color: Colors.textMuted, fontSize: 10 },

  banBtn: { padding: Spacing.xs },
});
