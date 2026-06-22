import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  Pressable,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useSettingsStore } from '@/stores/settingsStore';
import { testApiConnection } from '@/services/api';

type TestStatus = 'idle' | 'testing' | 'ok' | 'error';

export default function SetupScreen() {
  const router    = useRouter();
  const setApiUrl = useSettingsStore((s) => s.setApiUrl);

  const [url,    setUrl]    = useState('');
  const [status, setStatus] = useState<TestStatus>('idle');
  const [msg,    setMsg]    = useState('');
  const [saving, setSaving] = useState(false);

  const handleTest = async () => {
    const clean = url.trim().replace(/\/$/, '');
    if (!clean) { setMsg('Veuillez saisir une URL.'); setStatus('error'); return; }

    setStatus('testing');
    setMsg('');
    const result = await testApiConnection(clean);
    if (result.ok) {
      setStatus('ok');
      setMsg(result.message);
    } else {
      setStatus('error');
      setMsg(result.message);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    await setApiUrl(url.trim().replace(/\/$/, ''));
    setSaving(false);
    router.replace('/(tabs)');
  };

  const statusColor  = status === 'ok' ? Colors.success : Colors.error;
  const statusIcon   = status === 'ok'
    ? 'checkmark-circle'
    : 'alert-circle';

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Logo */}
          <View style={styles.logoBlock}>
            <View style={styles.logoCircle}>
              <Ionicons name="tv" size={40} color={Colors.primary} />
            </View>
            <Text style={styles.appName}>Anime Sama</Text>
            <Text style={styles.appTagline}>Votre catalogue personnel</Text>
          </View>

          {/* Carte configuration */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Configuration de l'API</Text>
            <Text style={styles.cardDesc}>
              Saisissez l'adresse de votre serveur Anime Sama pour continuer.
              L'application a besoin de cette connexion pour fonctionner.
            </Text>

            <TextInput
              style={styles.input}
              value={url}
              onChangeText={(t) => { setUrl(t); setStatus('idle'); setMsg(''); }}
              placeholder="ex : http://192.168.1.48:8000"
              placeholderTextColor={Colors.textMuted}
              autoCorrect={false}
              autoCapitalize="none"
              keyboardType="url"
              returnKeyType="done"
              onSubmitEditing={handleTest}
            />

            {/* Statut test */}
            {status !== 'idle' && status !== 'testing' && (
              <View style={[styles.statusBox, { borderColor: statusColor + '55', backgroundColor: statusColor + '15' }]}>
                <Ionicons name={statusIcon} size={16} color={statusColor} />
                <Text style={[styles.statusText, { color: statusColor }]} numberOfLines={2}>
                  {msg}
                </Text>
              </View>
            )}

            {/* Bouton test */}
            <Pressable
              style={[styles.testBtn, status === 'testing' && styles.btnDisabled]}
              onPress={handleTest}
              disabled={status === 'testing'}
            >
              {status === 'testing'
                ? <ActivityIndicator size="small" color={Colors.primary} />
                : <Ionicons name="wifi" size={16} color={Colors.primary} />
              }
              <Text style={styles.testBtnText}>
                {status === 'testing' ? 'Test en cours…' : 'Tester la connexion'}
              </Text>
            </Pressable>

            {/* Bouton sauvegarder — visible uniquement si connexion OK */}
            {status === 'ok' && (
              <Pressable
                style={[styles.saveBtn, saving && styles.btnDisabled]}
                onPress={handleSave}
                disabled={saving}
              >
                {saving
                  ? <ActivityIndicator size="small" color={Colors.text} />
                  : <Ionicons name="rocket" size={16} color={Colors.text} />
                }
                <Text style={styles.saveBtnText}>
                  {saving ? 'Démarrage…' : 'Sauvegarder et démarrer'}
                </Text>
              </Pressable>
            )}
          </View>

          {/* Aide */}
          <View style={styles.helpBlock}>
            <Ionicons name="information-circle-outline" size={14} color={Colors.textMuted} />
            <Text style={styles.helpText}>
              L'adresse doit être accessible depuis ce téléphone.{'\n'}
              Exemple Wi-Fi local : <Text style={{ color: Colors.primary }}>http://192.168.1.x:8000</Text>
            </Text>
          </View>

          {/* Infos développeur */}
          <View style={styles.devInfo}>
            <Text style={styles.devText}>Développé par Taïse De Thèse Yabie</Text>
            <Pressable onPress={() => Linking.openURL('https://github.com/gihamos/')}>
              <Text style={[styles.devText, styles.devLink]}>github : https://github.com/gihamos/</Text>
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.xxl,
    gap: Spacing.xl,
  },

  logoBlock: { alignItems: 'center', gap: Spacing.sm },
  logoCircle: {
    width: 88,
    height: 88,
    borderRadius: Radius.full,
    backgroundColor: Colors.primary + '22',
    borderWidth: 2,
    borderColor: Colors.primary + '55',
    justifyContent: 'center',
    alignItems: 'center',
  },
  appName: {
    color: Colors.text,
    fontSize: FontSize.xxxl,
    fontWeight: '900',
    letterSpacing: -0.5,
  },
  appTagline: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
  },

  card: {
    backgroundColor: Colors.card,
    borderRadius: Radius.xl,
    padding: Spacing.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.md,
  },
  cardTitle: {
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: '700',
  },
  cardDesc: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    lineHeight: 20,
  },

  input: {
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    color: Colors.text,
    fontSize: FontSize.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },

  statusBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.xs,
    padding: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  statusText: {
    flex: 1,
    fontSize: FontSize.sm,
    fontWeight: '500',
    lineHeight: 18,
  },

  testBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    paddingVertical: Spacing.md,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.primary,
    backgroundColor: Colors.primary + '15',
  },
  testBtnText: {
    color: Colors.primary,
    fontSize: FontSize.md,
    fontWeight: '700',
  },

  saveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    paddingVertical: Spacing.md,
    borderRadius: Radius.full,
    backgroundColor: Colors.primary,
  },
  saveBtnText: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: '700',
  },

  btnDisabled: { opacity: 0.6 },

  devInfo: {
    alignItems: 'center',
    gap: 4,
    paddingTop: Spacing.sm,
  },
  devText: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    textAlign: 'center',
    opacity: 0.7,
  },
  devLink: {
    color: Colors.primary,
    textDecorationLine: 'underline',
    opacity: 1,
  },

  helpBlock: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.xs,
  },
  helpText: {
    flex: 1,
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    lineHeight: 18,
  },
});
