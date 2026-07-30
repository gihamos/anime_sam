import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  TextInput,
  Alert,
  ActivityIndicator,
  Linking,
  Switch,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useAuthStore } from '@/stores/authStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { getApiError, testApiConnection, authApi } from '@/services/api';

type TestStatus = 'idle' | 'testing' | 'ok' | 'error';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, isAuthenticated, login, logout, isLoading } = useAuthStore();
  const {
    apiUrl, setApiUrl, externalPlayer, setExternalPlayer,
    notificationsEnabled, setNotificationsEnabled,
    notifyDownloads, setNotifyDownloads,
    notifyFavEpisodes, setNotifyFavEpisodes,
    notifyNewCatalogues, setNotifyNewCatalogues,
    notifyAnyUpdate, setNotifyAnyUpdate,
  } = useSettingsStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [apiUrlInput, setApiUrlInput]  = useState(apiUrl);
  const [testStatus,  setTestStatus]   = useState<TestStatus>('idle');
  const [testMsg,     setTestMsg]      = useState('');
  const [error, setError] = useState('');

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwSubmitting, setPwSubmitting] = useState(false);
  const [pwError, setPwError] = useState('');

  const closePasswordModal = () => {
    setShowPasswordModal(false);
    setCurrentPw(''); setNewPw(''); setConfirmPw(''); setPwError('');
  };

  const handleChangePassword = async () => {
    if (newPw.length < 8) { setPwError('Le nouveau mot de passe doit contenir au moins 8 caractères.'); return; }
    if (newPw !== confirmPw) { setPwError('Les deux mots de passe ne correspondent pas.'); return; }
    setPwError('');
    setPwSubmitting(true);
    try {
      await authApi.changePassword(currentPw, newPw);
      closePasswordModal();
      Alert.alert('Mot de passe modifié', 'Votre mot de passe a été mis à jour.');
    } catch (e) {
      setPwError(getApiError(e));
    } finally {
      setPwSubmitting(false);
    }
  };

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

  const handleTestApi = async () => {
    const clean = apiUrlInput.trim().replace(/\/$/, '');
    if (!clean) { setTestStatus('error'); setTestMsg('Veuillez saisir une URL.'); return; }
    setTestStatus('testing'); setTestMsg('');
    const result = await testApiConnection(clean);
    setTestStatus(result.ok ? 'ok' : 'error');
    setTestMsg(result.message);
  };

  const handleSaveApiUrl = async () => {
    const url = apiUrlInput.trim().replace(/\/$/, '');
    await setApiUrl(url);
    setApiUrlInput(url);
    setTestStatus('idle');
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

            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Sécurité</Text>
              <Pressable
                style={styles.adminLink}
                onPress={() => setShowPasswordModal(true)}
              >
                <View style={styles.adminLinkLeft}>
                  <View style={[styles.adminLinkIcon, { backgroundColor: Colors.primary + '22' }]}>
                    <Ionicons name="key-outline" size={18} color={Colors.primary} />
                  </View>
                  <Text style={styles.adminLinkLabel}>Changer le mot de passe</Text>
                </View>
                <Ionicons name="chevron-forward" size={16} color={Colors.textMuted} />
              </Pressable>
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

        {/* Section admin — visible uniquement pour le rôle admin */}
        {isAuthenticated && user?.role === 'admin' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Administration</Text>

            <Pressable style={styles.adminLink} onPress={() => router.push('/admin/connections')}>
              <View style={styles.adminLinkLeft}>
                <View style={[styles.adminLinkIcon, { backgroundColor: Colors.info + '22' }]}>
                  <Ionicons name="wifi" size={18} color={Colors.info} />
                </View>
                <View>
                  <Text style={styles.adminLinkLabel}>Connexions & IPs</Text>
                  <Text style={styles.adminLinkDesc}>Historique, statistiques, ban IP</Text>
                </View>
              </View>
              <Ionicons name="chevron-forward" size={16} color={Colors.textMuted} />
            </Pressable>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Lecture vidéo</Text>
          <View style={styles.permRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.permLabel}>Lecteur externe</Text>
              <Text style={styles.sectionDesc}>
                Propose de choisir une app vidéo installée (VLC, MX Player…) au lieu du lecteur intégré.
              </Text>
            </View>
            <Switch
              value={externalPlayer}
              onValueChange={setExternalPlayer}
              trackColor={{ false: Colors.border, true: Colors.primary + '88' }}
              thumbColor={externalPlayer ? Colors.primary : Colors.textMuted}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Notifications</Text>
          <View style={styles.permRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.permLabel}>Activer les notifications</Text>
              <Text style={styles.sectionDesc}>
                Notifications locales uniquement (l'app doit être ouverte ou récemment
                utilisée — pas de vraies notifications push dans Expo Go).
              </Text>
            </View>
            <Switch
              value={notificationsEnabled}
              onValueChange={(v) => { void setNotificationsEnabled(v); }}
              trackColor={{ false: Colors.border, true: Colors.primary + '88' }}
              thumbColor={notificationsEnabled ? Colors.primary : Colors.textMuted}
            />
          </View>

          {notificationsEnabled && (
            <>
              <View style={styles.permRow}>
                <Text style={styles.permLabel}>Téléchargements terminés</Text>
                <Switch
                  value={notifyDownloads}
                  onValueChange={setNotifyDownloads}
                  trackColor={{ false: Colors.border, true: Colors.primary + '88' }}
                  thumbColor={notifyDownloads ? Colors.primary : Colors.textMuted}
                />
              </View>
              <View style={styles.permRow}>
                <Text style={styles.permLabel}>Nouvel épisode sur mes favoris</Text>
                <Switch
                  value={notifyFavEpisodes}
                  onValueChange={setNotifyFavEpisodes}
                  trackColor={{ false: Colors.border, true: Colors.primary + '88' }}
                  thumbColor={notifyFavEpisodes ? Colors.primary : Colors.textMuted}
                />
              </View>
              <View style={styles.permRow}>
                <Text style={styles.permLabel}>Nouveaux catalogues</Text>
                <Switch
                  value={notifyNewCatalogues}
                  onValueChange={setNotifyNewCatalogues}
                  trackColor={{ false: Colors.border, true: Colors.primary + '88' }}
                  thumbColor={notifyNewCatalogues ? Colors.primary : Colors.textMuted}
                />
              </View>
              <View style={styles.permRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.permLabel}>Toute mise à jour de catalogue</Text>
                  <Text style={styles.sectionDesc}>Bruyant — désactivé par défaut.</Text>
                </View>
                <Switch
                  value={notifyAnyUpdate}
                  onValueChange={setNotifyAnyUpdate}
                  trackColor={{ false: Colors.border, true: Colors.primary + '88' }}
                  thumbColor={notifyAnyUpdate ? Colors.primary : Colors.textMuted}
                />
              </View>
            </>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Configuration API</Text>
          <Text style={styles.sectionDesc}>
            Connectée à : <Text style={{ color: Colors.primary }}>{apiUrl || '—'}</Text>
          </Text>

          <TextInput
            style={styles.input}
            value={apiUrlInput}
            onChangeText={(t) => { setApiUrlInput(t); setTestStatus('idle'); setTestMsg(''); }}
            placeholder="ex : http://192.168.1.48:8000"
            placeholderTextColor={Colors.textMuted}
            autoCorrect={false}
            autoCapitalize="none"
            keyboardType="url"
            returnKeyType="done"
            onSubmitEditing={handleTestApi}
          />

          {/* Résultat du test */}
          {testStatus !== 'idle' && testStatus !== 'testing' && (
            <View style={[
              styles.testStatusBox,
              testStatus === 'ok'
                ? { borderColor: Colors.success + '55', backgroundColor: Colors.success + '15' }
                : { borderColor: Colors.error   + '55', backgroundColor: Colors.error   + '15' },
            ]}>
              <Ionicons
                name={testStatus === 'ok' ? 'checkmark-circle' : 'alert-circle'}
                size={14}
                color={testStatus === 'ok' ? Colors.success : Colors.error}
              />
              <Text style={[
                styles.testStatusText,
                { color: testStatus === 'ok' ? Colors.success : Colors.error },
              ]} numberOfLines={2}>
                {testMsg}
              </Text>
            </View>
          )}

          <View style={styles.apiActions}>
            {/* Tester */}
            <Pressable
              style={[styles.testBtn, testStatus === 'testing' && { opacity: 0.6 }]}
              onPress={handleTestApi}
              disabled={testStatus === 'testing'}
            >
              {testStatus === 'testing'
                ? <ActivityIndicator size="small" color={Colors.primary} />
                : <Ionicons name="wifi" size={14} color={Colors.primary} />
              }
              <Text style={styles.testBtnText}>
                {testStatus === 'testing' ? 'Test…' : 'Tester'}
              </Text>
            </Pressable>

            {/* Sauvegarder */}
            <Pressable
              style={[styles.saveBtn, testStatus !== 'ok' && { opacity: 0.4 }]}
              onPress={handleSaveApiUrl}
              disabled={testStatus !== 'ok'}
            >
              <Ionicons name="save-outline" size={14} color={Colors.text} />
              <Text style={styles.saveBtnText}>Sauvegarder</Text>
            </Pressable>
          </View>
        </View>

        <View style={styles.appInfo}>
          <Text style={styles.appInfoTitle}>Anime Sama App v1.0.0</Text>
          <Text style={styles.appInfoText}>Développé par Taïse De Thèse Yabie</Text>
          <Pressable onPress={() => Linking.openURL('https://github.com/gihamos/')}>
            <Text style={[styles.appInfoText, styles.appInfoLink]}>github : https://github.com/gihamos/</Text>
          </Pressable>
          <View style={styles.appInfoDivider} />
          <Text style={styles.appInfoDisclaimer}>
            Cette application n'est pas affiliée à anime-sama.to
          </Text>
          <Text style={styles.appInfoDisclaimer}>
            et n'a aucun lien officiel avec ce site.
          </Text>
        </View>
      </ScrollView>

      <Modal visible={showPasswordModal} transparent animationType="slide" onRequestClose={closePasswordModal}>
        <View style={pwStyles.backdrop}>
          <View style={pwStyles.sheet}>
            <Text style={pwStyles.title}>Changer le mot de passe</Text>

            {pwError ? (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>{pwError}</Text>
              </View>
            ) : null}

            <TextInput
              style={styles.input}
              value={currentPw}
              onChangeText={setCurrentPw}
              placeholder="Mot de passe actuel"
              placeholderTextColor={Colors.textMuted}
              secureTextEntry
            />
            <TextInput
              style={styles.input}
              value={newPw}
              onChangeText={setNewPw}
              placeholder="Nouveau mot de passe (8 caractères min.)"
              placeholderTextColor={Colors.textMuted}
              secureTextEntry
            />
            <TextInput
              style={styles.input}
              value={confirmPw}
              onChangeText={setConfirmPw}
              placeholder="Confirmer le nouveau mot de passe"
              placeholderTextColor={Colors.textMuted}
              secureTextEntry
            />

            <View style={pwStyles.actions}>
              <Pressable style={pwStyles.cancelBtn} onPress={closePasswordModal}>
                <Text style={pwStyles.cancelText}>Annuler</Text>
              </Pressable>
              <Pressable
                style={[pwStyles.confirmBtn, (pwSubmitting || !currentPw || !newPw || !confirmPw) && { opacity: 0.5 }]}
                disabled={pwSubmitting || !currentPw || !newPw || !confirmPw}
                onPress={handleChangePassword}
              >
                {pwSubmitting
                  ? <ActivityIndicator size="small" color={Colors.text} />
                  : <Text style={pwStyles.confirmText}>Confirmer</Text>}
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
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
  adminLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  adminLinkLeft: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  adminLinkIcon: {
    width: 38,
    height: 38,
    borderRadius: Radius.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
  adminLinkLabel: { color: Colors.text, fontSize: FontSize.md, fontWeight: '600' },
  adminLinkDesc:  { color: Colors.textMuted, fontSize: FontSize.xs, marginTop: 2 },
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
  testStatusBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.xs,
    padding: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  testStatusText: {
    flex: 1,
    fontSize: FontSize.xs,
    fontWeight: '500',
    lineHeight: 17,
  },
  apiActions: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginTop: Spacing.xs,
  },
  testBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.primary,
    backgroundColor: Colors.primary + '15',
  },
  testBtnText: {
    color: Colors.primary,
    fontSize: FontSize.sm,
    fontWeight: '700',
  },
  saveBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    backgroundColor: Colors.primary,
  },
  saveBtnText: {
    color: Colors.text,
    fontSize: FontSize.sm,
    fontWeight: '700',
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
  appInfoLink: {
    color: Colors.primary,
    textDecorationLine: 'underline',
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

const pwStyles = StyleSheet.create({
  backdrop: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: Colors.card, borderTopLeftRadius: Radius.xl,
    borderTopRightRadius: Radius.xl, padding: Spacing.lg, gap: Spacing.md,
  },
  title: { color: Colors.text, fontSize: FontSize.lg, fontWeight: '700' },
  actions: { flexDirection: 'row', gap: Spacing.md, marginTop: Spacing.sm },
  cancelBtn: {
    flex: 1, paddingVertical: Spacing.md, alignItems: 'center',
    backgroundColor: Colors.surfaceAlt, borderRadius: Radius.md,
  },
  cancelText: { color: Colors.textMuted, fontWeight: '600' },
  confirmBtn: {
    flex: 2, paddingVertical: Spacing.md, alignItems: 'center',
    backgroundColor: Colors.primary, borderRadius: Radius.md,
  },
  confirmText: { color: Colors.text, fontWeight: '700', fontSize: FontSize.md },
});
