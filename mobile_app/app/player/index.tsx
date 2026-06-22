import React, { useState, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  StatusBar,
  useWindowDimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors, FontSize, Spacing, Radius } from '@/constants/colors';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { Video as ExpoVideo, ResizeMode, AVPlaybackStatus } from 'expo-av';
import { usePlayerStore } from '@/stores/playerStore';

// L'orientation est gérée par le système (rotation naturelle du téléphone).
// Le player s'adapte via useWindowDimensions — pas de verrouillage programmatique.

function isNativePlayable(url: string, player: string): boolean {
  if (player === 'local') return true;
  const lower = url.toLowerCase();
  return lower.endsWith('.mp4') || lower.endsWith('.mkv') || lower.endsWith('.m3u8');
}

function buildEmbedHtml(url: string): string {
  return `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #000; width: 100vw; height: 100vh; overflow: hidden; }
  iframe { width: 100%; height: 100%; border: none; }
</style>
</head>
<body>
  <iframe src="${url}" allowfullscreen allow="autoplay; fullscreen; encrypted-media"></iframe>
</body>
</html>`;
}

// ─── Player natif (expo-av) pour fichiers locaux / MP4 ───────────────────────

function NativePlayer({ url, subtitle }: { url: string; subtitle: string }) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const videoRef = useRef<ExpoVideo>(null);
  const [status, setStatus] = useState<AVPlaybackStatus | null>(null);
  const [showControls, setShowControls] = useState(true);
  const controlsTimer = useRef<ReturnType<typeof setTimeout>>();

  const isPlaying   = status?.isLoaded && status.isPlaying;
  const isBuffering = status?.isLoaded && status.isBuffering;
  const isLoaded    = status?.isLoaded;
  const position    = status?.isLoaded ? status.positionMillis : 0;
  const duration    = status?.isLoaded && status.durationMillis ? status.durationMillis : 0;
  const progress    = duration > 0 ? position / duration : 0;

  const formatTime = (ms: number) => {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    if (h > 0) return `${h}:${String(m % 60).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
    return `${m}:${String(s % 60).padStart(2, '0')}`;
  };

  const resetControlsTimer = useCallback(() => {
    if (controlsTimer.current) clearTimeout(controlsTimer.current);
    setShowControls(true);
    controlsTimer.current = setTimeout(() => setShowControls(false), 3000);
  }, []);

  const togglePlay = async () => {
    if (!videoRef.current) return;
    isPlaying ? await videoRef.current.pauseAsync() : await videoRef.current.playAsync();
    resetControlsTimer();
  };

  const seek = async (delta: number) => {
    if (!videoRef.current || !isLoaded) return;
    await videoRef.current.setPositionAsync(Math.max(0, position + delta * 1000));
    resetControlsTimer();
  };

  return (
    <View style={styles.container}>
      <StatusBar hidden />
      <Pressable style={styles.videoWrapper} onPress={resetControlsTimer}>
        <ExpoVideo
          ref={videoRef}
          source={{ uri: url }}
          style={{ width, height }}
          resizeMode={ResizeMode.CONTAIN}
          shouldPlay
          onPlaybackStatusUpdate={setStatus}
          useNativeControls={false}
        />

        {isBuffering && (
          <View style={styles.overlay}>
            <ActivityIndicator size="large" color={Colors.primary} />
          </View>
        )}

        {showControls && (
          <View style={styles.controls}>
            <View style={[styles.topBar, { paddingTop: insets.top + Spacing.sm }]}>
              <Pressable style={styles.backBtn} onPress={() => router.back()}>
                <Ionicons name="chevron-back" size={24} color={Colors.text} />
              </Pressable>
              <Text style={styles.titleText} numberOfLines={1}>{subtitle}</Text>
            </View>

            <View style={styles.centerControls}>
              <Pressable onPress={() => seek(-10)}>
                <View style={styles.seekBtn}>
                  <Ionicons name="play-back" size={28} color={Colors.text} />
                  <Text style={styles.seekLabel}>10s</Text>
                </View>
              </Pressable>
              <Pressable style={styles.playBtn} onPress={togglePlay}>
                <Ionicons name={isPlaying ? 'pause' : 'play'} size={40} color={Colors.text} />
              </Pressable>
              <Pressable onPress={() => seek(10)}>
                <View style={styles.seekBtn}>
                  <Ionicons name="play-forward" size={28} color={Colors.text} />
                  <Text style={styles.seekLabel}>10s</Text>
                </View>
              </Pressable>
            </View>

            <View style={[styles.bottomBar, { paddingBottom: insets.bottom + Spacing.md }]}>
              <Text style={styles.timeText}>{formatTime(position)}</Text>
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
                <View style={[styles.progressThumb, { left: `${progress * 100}%` }]} />
              </View>
              <Text style={styles.timeText}>{formatTime(duration)}</Text>
            </View>
          </View>
        )}
      </Pressable>
    </View>
  );
}

// ─── Player WebView pour les URLs d'embed (sendvid, gogo, etc.) ──────────────

function WebPlayer({ url, subtitle }: { url: string; subtitle: string }) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const [loading, setLoading] = useState(true);
  const [showHeader, setShowHeader] = useState(true);
  const hideTimer = useRef<ReturnType<typeof setTimeout>>();

  const toggleHeader = () => {
    if (hideTimer.current) clearTimeout(hideTimer.current);
    setShowHeader(true);
    hideTimer.current = setTimeout(() => setShowHeader(false), 3000);
  };

  return (
    <View style={styles.container}>
      <StatusBar hidden />

      <WebView
        source={{ html: buildEmbedHtml(url), baseUrl: url }}
        style={{ width, height }}
        allowsInlineMediaPlayback
        mediaPlaybackRequiresUserAction={false}
        allowsFullscreenVideo
        javaScriptEnabled
        domStorageEnabled
        onLoadStart={() => setLoading(true)}
        onLoadEnd={() => setLoading(false)}
        onTouchStart={toggleHeader}
        userAgent="Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
      />

      {loading && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Chargement du lecteur…</Text>
        </View>
      )}

      {showHeader && (
        <View style={[styles.webTopBar, { paddingTop: insets.top + Spacing.sm }]}>
          <Pressable style={styles.backBtn} onPress={() => router.back()}>
            <Ionicons name="chevron-back" size={24} color={Colors.text} />
          </Pressable>
          <Text style={styles.titleText} numberOfLines={1}>{subtitle}</Text>
        </View>
      )}
    </View>
  );
}

// ─── Main ────────────────────────────────────────────────────────────────────

export default function PlayerScreen() {
  const { url, player, title, episode, saison } = usePlayerStore();
  const router = useRouter();

  const subtitle = [
    title,
    saison  ? `${saison}` : null,
    episode ? `Épisode ${episode}` : null,
  ].filter(Boolean).join(' · ');

  if (!url) {
    return (
      <View style={[styles.container, styles.overlay]}>
        <Ionicons name="alert-circle" size={48} color={Colors.error} />
        <Text style={{ color: Colors.text, marginTop: Spacing.md }}>Aucune vidéo sélectionnée</Text>
        <Pressable style={[styles.backBtn, { marginTop: Spacing.lg }]} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={24} color={Colors.text} />
        </Pressable>
      </View>
    );
  }

  if (isNativePlayable(url, player)) {
    return <NativePlayer url={url} subtitle={subtitle} />;
  }

  return <WebPlayer url={url} subtitle={subtitle} />;
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: '#000' },
  videoWrapper: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
  },
  loadingText: { color: Colors.textSecondary, marginTop: Spacing.md, fontSize: FontSize.sm },
  controls: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'space-between',
  },
  topBar: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: Spacing.lg, gap: Spacing.md,
  },
  webTopBar: {
    position: 'absolute', top: 0, left: 0, right: 0,
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: Spacing.lg, gap: Spacing.md,
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingBottom: Spacing.sm,
  },
  backBtn: {
    width: 40, height: 40, borderRadius: Radius.full,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center', alignItems: 'center',
  },
  titleText: { flex: 1, color: Colors.text, fontSize: FontSize.md, fontWeight: '700' },
  centerControls: {
    flexDirection: 'row', justifyContent: 'center',
    alignItems: 'center', gap: Spacing.xxl,
  },
  seekBtn:   { alignItems: 'center', gap: 4 },
  seekLabel: { color: Colors.textSecondary, fontSize: FontSize.xs },
  playBtn: {
    width: 70, height: 70, borderRadius: Radius.full,
    backgroundColor: 'rgba(124,106,247,0.8)',
    justifyContent: 'center', alignItems: 'center',
  },
  bottomBar: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: Spacing.lg, gap: Spacing.sm,
  },
  timeText: {
    color: Colors.text, fontSize: FontSize.xs,
    fontVariant: ['tabular-nums'], minWidth: 42,
  },
  progressBar: {
    flex: 1, height: 3,
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: Radius.full, position: 'relative',
  },
  progressFill: {
    height: '100%', backgroundColor: Colors.primary, borderRadius: Radius.full,
  },
  progressThumb: {
    position: 'absolute', top: -5, width: 13, height: 13,
    borderRadius: Radius.full, backgroundColor: Colors.primary, marginLeft: -6,
  },
});
