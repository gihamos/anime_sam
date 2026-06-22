import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  TextInput,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useAuthStore } from '@/stores/authStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { getApiError } from '@/services/api';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, isAuthenticated, login, logout, isLoading } = useAuthStore();
  const { apiUrl, setApiUrl } = useSettingsStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [apiUrlInput, setApiUrlInput] = useState(apiUrl);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!username || !password) return;
    setError('');
    try {
      await login(username, password);
    } catch (e) {
      setError(getApiError(e));
    }
  };

  const handleLogout = () => {
    Alert.alert('Déconnexion', 'Se déconnecter ?', [
      { text: 'Annuler', style: 'cancel' },
      { text: 'Oui', style: 'destructive', onPress: logout },
    ]);
  };

  const handleSaveApiUrl = async () => {
    const url = apiUrlInput.trim().replace(/\/$/, '');
    await setApiUrl(url);
    setApiUrlInput(url);
    Alert.alert('Sauvegardé', 'URL de l\'API mise à jour.');
  };

  const roleColor: Record<string, string> = {
    admin: Colors.accent,
    user: Colors.primary,
    client: Colors.info,
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.title}>Profil</Text>
        </View>

        {isAuthenticated && user ? (
          <>
            <View style={styles.userCard}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{user.username[0].toUpperCase()}</Text>
              </View>
              <View style={styles.userInfo}>
                <Text style={styles.username}>{user.username}</Text>
                {user.email && <Text style={styles.email}>{user.email}</Text>}
                <View style={[styles.roleBadge, { backgroundColor: (roleColor[user.role] || Colors.primary) + '33' }]}>
                  <Text style={[styles.roleText, { color: roleColor[user.role] || Colors.primary }]}>
                    {user.role.toUpperCase()}
                  </Text>
                </View>
              </View>
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Permissions</Text>
              {[
                { label: 'Synchronisation', key: 'can_sync' as const },
                { label: 'Téléchargement', key: 'can_download' as const },
                { label: 'Rafraîchissement', key: 'can_refresh' as const },
                { label: 'Suppression', key: 'can_delete' as const },
              ].map(({ label, key }) => (
                <View key={key} style={styles.permRow}>
                  <Text style={styles.permLabel}>{label}</Text>
                  <Ionicons
                    name={user.permissions[key] ? 'checkmark-circle' : 'close-circle'}
                    size={20}
                    color={user.permissions[key] ? Colors.success : Colors.textMuted}
                  />
                </View>
              ))}
            </View>

            <Pressable style={styles.logoutBtn} onPress={handleLogout}>
              <Ionicons name="log-out-outline" size={20} color={Colors.error} />
              <Text style={styles.logoutText}>Se déconnecter</Text>
            </Pressable>
          </>
        ) : (
          <View style={styles.loginCard}>
            <Text style={styles.loginTitle}>Connexion</Text>
            <Text style={styles.loginSubtitle}>
              Connectez-vous pour accéder à toutes les fonctionnalités.
            </Text>

            {error ? (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            <TextInput
              style={styles.input}
              value={username}
              onChangeText={setUsername}
              placeholder="Nom d'utilisateur"
              placeholderTextColor={Colors.textMuted}
              autoCorrect={false}
              autoCapitalize="none"
            />
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="Mot de passe"
              placeholderTextColor={Colors.textMuted}
              secureTextEntry
            />
            <Pressable
              style={[styles.loginBtn, isLoading && styles.loginBtnDisabled]}
              onPress={handleLogin}
              disabled={isLoading}
            >
              <Text style={styles.loginBtnText}>
                {isLoading ? 'Connexion...' : 'Se connecter'}
              </Text>
            </Pressable>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Configuration API</Text>
          <Text style={styles.sectionDesc}>
            URL actuelle : <Text style={{ color: Colors.primary }}>{apiUrl}</Text>
          </Text>

          {/* Raccourcis */}
          <Text style={styles.hintLabel}>Sélection rapide :</Text>
          <View style={styles.hintRow}>
            {[
              { label: 'Émulateur Android', url: 'http://10.0.2.2:8000' },
              { label: 'Wi-Fi (192.168.1.48)', url: 'http://192.168.1.48:8000' },
              { label: 'Localhost', url: 'http://localhost:8000' },
            ].map(({ label, url }) => (
              <Pressable
                key={url}
                style={[styles.hintChip, apiUrlInput === url && styles.hintChipActive]}
                onPress={() => setApiUrlInput(url)}
              >
                <Text style={[styles.hintChipText, apiUrlInput === url && styles.hintChipTextActive]}>
                  {label}
                </Text>
              </Pressable>
            ))}
          </View>

          <TextInput
            style={[styles.input, { marginTop: Spacing.sm }]}
            value={apiUrlInput}
            onChangeText={setApiUrlInput}
            placeholder="http://192.168.1.x:8000"
            placeholderTextColor={Colors.textMuted}
            autoCorrect={false}
            autoCapitalize="none"
            keyboardType="url"
          />
          <Pressable style={styles.saveBtn} onPress={handleSaveApiUrl}>
            <Text style={styles.saveBtnText}>Sauvegarder et reconnecter</Text>
          </Pressable>
        </View>

        <View style={styles.appInfo}>
          <Text style={styles.appInfoTitle}>Anime Sama App v1.0.0</Text>
          <Text style={styles.appInfoText}>Développé par Taïse de thèse Yabie</Text>
          <Text style={styles.appInfoText}>github.com/gihamos</Text>
          <View style={styles.appInfoDivider} />
          <Text style={styles.appInfoDisclaimer}>
            Cette application n'est pas affiliée à anime-sama.to
          </Text>
          <Text style={styles.appInfoDisclaimer}>
            et n'a aucun lien officiel avec ce site.
          </Text>
        </View>
      </ScrollView>
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
  userCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    marginHorizontal: Spacing.lg,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    gap: Spacing.md,
    marginBottom: Spacing.xl,
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: Radius.full,
    backgroundColor: Colors.primary + '44',
    borderWidth: 2,
    borderColor: Colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: Colors.primary,
    fontSize: FontSize.xxl,
    fontWeight: '800',
  },
  userInfo: { flex: 1, gap: 4 },
  username: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: '700',
  },
  email: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
  roleBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: Radius.sm,
    marginTop: 4,
  },
  roleText: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    letterSpacing: 1,
  },
  section: {
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.xl,
  },
  sectionTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: '700',
    marginBottom: Spacing.sm,
  },
  sectionDesc: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    marginBottom: Spacing.md,
  },
  permRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  permLabel: {
    color: Colors.textSecondary,
    fontSize: FontSize.md,
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.xl,
    padding: Spacing.md,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.error + '55',
  },
  logoutText: {
    color: Colors.error,
    fontSize: FontSize.md,
    fontWeight: '600',
  },
  loginCard: {
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.xl,
    gap: Spacing.md,
  },
  loginTitle: {
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: '700',
  },
  loginSubtitle: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
  },
  errorBox: {
    backgroundColor: Colors.error + '22',
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.error + '55',
  },
  errorText: {
    color: Colors.error,
    fontSize: FontSize.sm,
  },
  input: {
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.md,
    padding: Spacing.md,
    color: Colors.text,
    fontSize: FontSize.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  loginBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
    padding: Spacing.md,
    alignItems: 'center',
  },
  loginBtnDisabled: {
    opacity: 0.6,
  },
  loginBtnText: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: '700',
  },
  saveBtn: {
    backgroundColor: Colors.primary + '33',
    borderRadius: Radius.full,
    padding: Spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.primary,
    marginTop: Spacing.sm,
  },
  saveBtnText: {
    color: Colors.primary,
    fontSize: FontSize.md,
    fontWeight: '700',
  },
  hintLabel: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    marginBottom: Spacing.xs,
    marginTop: Spacing.sm,
  },
  hintRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.xs,
    marginBottom: Spacing.xs,
  },
  hintChip: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 5,
    borderRadius: Radius.full,
    backgroundColor: Colors.surfaceAlt,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  hintChipActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primary + '22',
  },
  hintChipText: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    fontWeight: '600',
  },
  hintChipTextActive: {
    color: Colors.primary,
  },
  appInfo: {
    alignItems: 'center',
    paddingBottom: Spacing.xxl,
    paddingHorizontal: Spacing.lg,
    gap: 4,
  },
  appInfoTitle: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    fontWeight: '600',
    marginBottom: 2,
  },
  appInfoText: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
  },
  appInfoDivider: {
    width: 40,
    height: 1,
    backgroundColor: Colors.border,
    marginVertical: Spacing.xs,
  },
  appInfoDisclaimer: {
    color: Colors.textMuted,
    fontSize: 10,
    textAlign: 'center',
    opacity: 0.6,
  },
});
