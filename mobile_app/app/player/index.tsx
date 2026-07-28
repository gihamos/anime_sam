import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  StatusBar,
  useWindowDimensions,
  PanResponder,
  Linking,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as IntentLauncher from 'expo-intent-launcher';
import { Colors, FontSize, Spacing, Radius } from '@/constants/colors';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useEvent } from 'expo';
import { usePlayerStore } from '@/stores/playerStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { streamApi } from '@/services/api';

// L'orientation est gérée par le système (rotation naturelle du téléphone).
// Le player s'adapte via useWindowDimensions — pas de verrouillage programmatique.

const SPEEDS = [0.5, 1, 1.25, 1.5, 2];

function isDirectPlayable(url: string): boolean {
  const clean = url.toLowerCase().split('?')[0];
  return clean.endsWith('.mp4') || clean.endsWith('.mkv') || clean.endsWith('.m3u8') || clean.endsWith('.webm');
}

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

function formatTime(seconds: number): string {
  const s = Math.floor(seconds % 60);
  const m = Math.floor(seconds / 60) % 60;
  const h = Math.floor(seconds / 3600);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
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

// ─── Résolution du flux ────────────────────────────────────────────────────────
// Détermine si l'URL sélectionnée est déjà lisible nativement (local, mp4, m3u8…)
// ou si elle doit d'abord passer par /api/stream/resolve pour obtenir un flux direct.

type StreamPhase = 'checking' | 'resolving' | 'native' | 'webview';

type SourceContentType = 'hls' | 'progressive';

function contentTypeFromExt(ext: string): SourceContentType {
  return ext.toLowerCase() === 'm3u8' ? 'hls' : 'progressive';
}

function useResolvedStream(url: string, player: string) {
  const [phase, setPhase] = useState<StreamPhase>('checking');
  const [source, setSource] = useState<{ uri: string; headers?: Record<string, string>; contentType?: SourceContentType } | null>(null);
  const apiUrl = useSettingsStore((s) => s.apiUrl);

  useEffect(() => {
    let cancelled = false;

    async function resolve() {
      if (!url) return;

      if (player === 'local' || isDirectPlayable(url)) {
        // L'URL du proxy/CDN ne se termine pas toujours par une extension
        // reconnaissable par le lecteur (query params) : on déduit le type
        // depuis l'extension réelle plutôt que de laisser ExoPlayer deviner.
        const clean = url.toLowerCase().split('?')[0];
        setSource({ uri: url, contentType: clean.endsWith('.m3u8') ? 'hls' : 'progressive' });
        setPhase('native');
        return;
      }

      setPhase('resolving');
      try {
        const result = await streamApi.resolve(url);
        if (cancelled) return;
        // Flux vidéo/audio séparés : pas de muxing natif fiable → on retombe sur l'embed.
        if (!result.url || result.merged) {
          setPhase('webview');
          return;
        }
        // proxy_url : headers déjà injectés côté serveur, aucun header requis côté
        // lecteur → fonctionne aussi bien avec le lecteur interne qu'un lecteur
        // externe (VLC…), et couvre les segments HLS individuels. À défaut, on
        // retombe sur l'URL directe + headers (moins fiable pour du HLS).
        // L'URL du proxy n'a pas d'extension .m3u8 reconnaissable par le lecteur
        // (c'est une query string) → on force le contentType explicitement,
        // sinon ExoPlayer tente de la lire comme un fichier progressif classique
        // et aucun extracteur ne reconnaît le texte M3U8 ("None of the available
        // extractors could read the stream").
        const contentType = contentTypeFromExt(result.ext);
        if (result.proxy_url) {
          setSource({ uri: `${apiUrl}${result.proxy_url}`, contentType });
        } else {
          setSource({ uri: result.url, headers: result.headers, contentType });
        }
        setPhase('native');
      } catch {
        if (!cancelled) setPhase('webview');
      }
    }

    resolve();
    return () => { cancelled = true; };
  }, [url, player, apiUrl]);

  return { phase, source, fallbackToWebview: () => setPhase('webview') };
}

// ─── Player natif (expo-video) ─────────────────────────────────────────────────

function NativePlayer({
  source,
  subtitle,
  onFallback,
}: {
  source: { uri: string; headers?: Record<string, string>; contentType?: SourceContentType };
  subtitle: string;
  onFallback: () => void;
}) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();

  const player = useVideoPlayer({ uri: source.uri, headers: source.headers, contentType: source.contentType }, (p) => {
    p.timeUpdateEventInterval = 0.5;
    p.play();
  });

  const { status, error } = useEvent(player, 'statusChange', { status: player.status, error: undefined });
  const { isPlaying } = useEvent(player, 'playingChange', { isPlaying: player.playing });
  const { currentTime: position } = useEvent(player, 'timeUpdate', {
    currentTime: player.currentTime, currentLiveTimestamp: null, currentOffsetFromLive: null, bufferedPosition: 0,
  });
  const duration = player.duration;
  const isBuffering = status === 'loading';
  const errorMsg = status === 'error' ? (error?.message || 'Impossible de lire ce flux.') : null;

  const [speed, setSpeed]           = useState(1);
  const [showControls, setShowControls] = useState(true);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const [seeking, setSeeking]       = useState(false);
  const [seekProgress, setSeekProgress] = useState(0);
  const [seekFlash, setSeekFlash]   = useState<'back' | 'forward' | null>(null);

  const controlsTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const flashTimer     = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const isPlayingRef   = useRef(isPlaying);
  const dragRef         = useRef(0);
  const barRef          = useRef<View>(null);
  const barLayout        = useRef({ x: 0, width: 1 });
  const lastTapLeft     = useRef(0);
  const lastTapRight    = useRef(0);

  useEffect(() => { isPlayingRef.current = isPlaying; }, [isPlaying]);

  const resetControlsTimer = useCallback(() => {
    if (controlsTimer.current) clearTimeout(controlsTimer.current);
    setShowControls(true);
    controlsTimer.current = setTimeout(() => {
      if (isPlayingRef.current) setShowControls(false);
    }, 3500);
  }, []);

  useEffect(() => {
    resetControlsTimer();
    return () => {
      if (controlsTimer.current) clearTimeout(controlsTimer.current);
      if (flashTimer.current) clearTimeout(flashTimer.current);
    };
  }, [resetControlsTimer]);

  const togglePlay = () => {
    isPlaying ? player.pause() : player.play();
    resetControlsTimer();
  };

  const seekBy = (delta: number) => {
    player.currentTime = clamp(player.currentTime + delta, 0, player.duration || Infinity);
    resetControlsTimer();
  };

  const flashSeek = (side: 'back' | 'forward') => {
    if (flashTimer.current) clearTimeout(flashTimer.current);
    setSeekFlash(side);
    flashTimer.current = setTimeout(() => setSeekFlash(null), 500);
  };

  const handleZoneTap = (side: 'left' | 'right') => {
    const now = Date.now();
    const lastTapRef = side === 'left' ? lastTapLeft : lastTapRight;
    if (now - lastTapRef.current < 300) {
      lastTapRef.current = 0;
      seekBy(side === 'left' ? -10 : 10);
      flashSeek(side === 'left' ? 'back' : 'forward');
    } else {
      lastTapRef.current = now;
      resetControlsTimer();
      setShowControls((v) => !v);
    }
  };

  const measureBar = () => {
    barRef.current?.measure((_x, _y, w, _h, pageX) => {
      barLayout.current = { x: pageX, width: w || 1 };
    });
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt) => {
        measureBar();
        if (controlsTimer.current) clearTimeout(controlsTimer.current);
        const p = clamp((evt.nativeEvent.pageX - barLayout.current.x) / barLayout.current.width, 0, 1);
        dragRef.current = p;
        setSeeking(true);
        setSeekProgress(p);
      },
      onPanResponderMove: (evt) => {
        const p = clamp((evt.nativeEvent.pageX - barLayout.current.x) / barLayout.current.width, 0, 1);
        dragRef.current = p;
        setSeekProgress(p);
      },
      onPanResponderRelease: () => {
        player.currentTime = dragRef.current * player.duration;
        setSeeking(false);
        resetControlsTimer();
      },
    })
  ).current;

  const setPlaybackSpeed = (s: number) => {
    setSpeed(s);
    player.playbackRate = s;
    setShowSpeedMenu(false);
    resetControlsTimer();
  };

  const retry = () => {
    player.replace({ uri: source.uri, headers: source.headers, contentType: source.contentType });
    resetControlsTimer();
  };

  const progress = seeking ? seekProgress : (duration > 0 ? position / duration : 0);

  if (errorMsg) {
    return (
      <View style={styles.container}>
        <StatusBar hidden />
        <View style={styles.overlay}>
          <Ionicons name="alert-circle" size={48} color={Colors.error} />
          <Text style={styles.errorText}>{errorMsg}</Text>
          <View style={styles.errorActions}>
            <Pressable style={styles.errorBtn} onPress={retry}>
              <Text style={styles.errorBtnText}>Réessayer</Text>
            </Pressable>
            <Pressable style={[styles.errorBtn, styles.errorBtnSecondary]} onPress={onFallback}>
              <Text style={styles.errorBtnText}>Lecteur alternatif</Text>
            </Pressable>
          </View>
          <Pressable style={[styles.backBtn, { marginTop: Spacing.lg }]} onPress={() => router.back()}>
            <Ionicons name="chevron-back" size={24} color={Colors.text} />
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar hidden />

      <VideoView
        player={player}
        style={{ width, height, position: 'absolute' }}
        contentFit="contain"
        nativeControls={false}
        allowsFullscreen={false}
      />

      {/* Zones de double-tap pour avancer / reculer de 10s */}
      <View style={styles.tapZones} pointerEvents="box-none">
        <Pressable style={styles.tapZone} onPress={() => handleZoneTap('left')} />
        <View style={styles.tapZoneCenter} pointerEvents="none" />
        <Pressable style={styles.tapZone} onPress={() => handleZoneTap('right')} />
      </View>

      {seekFlash && (
        <View style={[styles.seekFlash, seekFlash === 'back' ? styles.seekFlashLeft : styles.seekFlashRight]} pointerEvents="none">
          <Ionicons name={seekFlash === 'back' ? 'play-back' : 'play-forward'} size={30} color={Colors.text} />
          <Text style={styles.seekFlashText}>10s</Text>
        </View>
      )}

      {isBuffering && !errorMsg && (
        <View style={styles.overlay} pointerEvents="none">
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      )}

      {showControls && (
        <View style={styles.controls} pointerEvents="box-none">
          <View style={[styles.topBar, { paddingTop: insets.top + Spacing.sm }]}>
            <Pressable style={styles.backBtn} onPress={() => router.back()}>
              <Ionicons name="chevron-back" size={24} color={Colors.text} />
            </Pressable>
            <Text style={styles.titleText} numberOfLines={1}>{subtitle}</Text>
            <Pressable
              style={styles.speedBtn}
              onPress={() => { setShowSpeedMenu((v) => !v); resetControlsTimer(); }}
            >
              <Text style={styles.speedBtnText}>{speed}x</Text>
            </Pressable>
          </View>

          {showSpeedMenu && (
            <View style={[styles.speedMenu, { top: insets.top + Spacing.sm + 44 }]}>
              {SPEEDS.map((s) => (
                <Pressable
                  key={s}
                  style={styles.speedOption}
                  onPress={() => setPlaybackSpeed(s)}
                >
                  <Text style={[styles.speedOptionText, s === speed && styles.speedOptionActive]}>
                    {s}x
                  </Text>
                  {s === speed && <Ionicons name="checkmark" size={16} color={Colors.primary} />}
                </Pressable>
              ))}
            </View>
          )}

          <View style={styles.centerControls}>
            <Pressable onPress={() => { seekBy(-10); resetControlsTimer(); }}>
              <View style={styles.seekBtn}>
                <Ionicons name="play-back" size={28} color={Colors.text} />
                <Text style={styles.seekLabel}>10s</Text>
              </View>
            </Pressable>
            <Pressable style={styles.playBtn} onPress={togglePlay}>
              <Ionicons name={isPlaying ? 'pause' : 'play'} size={40} color={Colors.text} />
            </Pressable>
            <Pressable onPress={() => { seekBy(10); resetControlsTimer(); }}>
              <View style={styles.seekBtn}>
                <Ionicons name="play-forward" size={28} color={Colors.text} />
                <Text style={styles.seekLabel}>10s</Text>
              </View>
            </Pressable>
          </View>

          <View style={[styles.bottomBar, { paddingBottom: insets.bottom + Spacing.md }]}>
            <Text style={styles.timeText}>{formatTime(seeking ? seekProgress * duration : position)}</Text>
            <View
              ref={barRef}
              style={styles.progressBar}
              onLayout={measureBar}
              hitSlop={{ top: 12, bottom: 12 }}
              {...panResponder.panHandlers}
            >
              <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
              <View style={[
                styles.progressThumb,
                { left: `${progress * 100}%` },
                seeking && styles.progressThumbActive,
              ]} />
            </View>
            <Text style={styles.timeText}>{formatTime(duration)}</Text>
          </View>
        </View>
      )}
    </View>
  );
}

// ─── Player WebView pour les URLs d'embed (fallback) ──────────────────────────

function WebPlayer({ url, subtitle }: { url: string; subtitle: string }) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const [loading, setLoading] = useState(true);
  const [showHeader, setShowHeader] = useState(true);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

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

// ─── Lecteur externe ────────────────────────────────────────────────────────────
// Délègue la lecture à l'app choisie par l'utilisateur via le sélecteur système
// Android (ACTION_VIEW, type video/*). Si aucune app ne le prend en charge, on
// propose de retomber sur le lecteur intégré pour cette lecture.

function ExternalPlayerLauncher({
  source,
  subtitle,
  onFallback,
}: {
  source: { uri: string; headers?: Record<string, string> };
  subtitle: string;
  onFallback: () => void;
}) {
  const router = useRouter();
  const [status, setStatus] = useState<'launching' | 'opened' | 'failed'>('launching');
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  // Empêche deux appels concurrents à startActivityAsync : le module natif ne
  // supporte qu'un seul appel en vol (il attend un onActivityResult) — un double
  // déclenchement (StrictMode, double-tap sur "Réessayer"…) provoque sinon
  // l'erreur "IntentLauncher activity is already started".
  const inFlightRef = useRef(false);

  const open = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setStatus('launching');
    setErrorDetail(null);
    try {
      if (Platform.OS === 'android') {
        // Déclenche le sélecteur système Android ("Ouvrir avec…") : toute app qui
        // gère video/* (VLC, MX Player, lecteur par défaut…) apparaît au choix.
        // IMPORTANT : ne PAS ajouter FLAG_ACTIVITY_NEW_TASK ici — startActivityAsync
        // attend un résultat (onActivityResult), et NEW_TASK empêche Android de le
        // router, ce qui bloque définitivement le module ("activity already started")
        // dès le premier appel.
        const result = await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
          data: source.uri,
          type: 'video/*',
          flags: 1, // FLAG_GRANT_READ_URI_PERMISSION
        });
        // `startActivityAsync` peut se résoudre SANS erreur même si aucune app n'a
        // réellement ouvert la vidéo (sélecteur annulé/fermé) → resultCode Canceled.
        if (result.resultCode === IntentLauncher.ResultCode.Canceled) {
          setErrorDetail("Aucune application n'a été choisie, ou elle n'a pas pu lire la vidéo.");
          setStatus('failed');
          return;
        }
      } else {
        // iOS n'a pas d'équivalent générique au chooser Android pour une URL distante.
        await Linking.openURL(source.uri);
      }
      setStatus('opened');
    } catch (err: any) {
      setErrorDetail(err?.message ?? String(err));
      setStatus('failed');
    } finally {
      inFlightRef.current = false;
    }
  }, [source.uri]);

  useEffect(() => { open(); }, [open]);

  return (
    <View style={styles.container}>
      <StatusBar hidden />
      <View style={styles.overlay}>
        {status === 'launching' && (
          <>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Text style={styles.loadingText}>Ouverture dans le lecteur externe…</Text>
          </>
        )}
        {status === 'opened' && (
          <>
            <Ionicons name="checkmark-circle" size={48} color={Colors.success} />
            <Text style={{ color: Colors.text, marginTop: Spacing.md, textAlign: 'center', paddingHorizontal: Spacing.xl }}>
              {subtitle || 'Vidéo'} ouverte dans le lecteur externe.
            </Text>
          </>
        )}
        {status === 'failed' && (
          <>
            <Ionicons name="alert-circle" size={48} color={Colors.error} />
            <Text style={styles.errorText}>
              Impossible d'ouvrir un lecteur externe (aucune app vidéo installée ?).
            </Text>
            {errorDetail && (
              <Text style={[styles.errorText, { fontSize: FontSize.xs, opacity: 0.7, marginTop: Spacing.xs }]}>
                {errorDetail}
              </Text>
            )}
            <View style={styles.errorActions}>
              <Pressable style={styles.errorBtn} onPress={open}>
                <Text style={styles.errorBtnText}>Réessayer</Text>
              </Pressable>
              <Pressable style={[styles.errorBtn, styles.errorBtnSecondary]} onPress={onFallback}>
                <Text style={styles.errorBtnText}>Lecteur intégré</Text>
              </Pressable>
            </View>
          </>
        )}
        <Pressable style={[styles.backBtn, { marginTop: Spacing.lg }]} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={24} color={Colors.text} />
        </Pressable>
      </View>
    </View>
  );
}

// ─── Main ────────────────────────────────────────────────────────────────────

export default function PlayerScreen() {
  const { url, player, title, episode, saison } = usePlayerStore();
  const router = useRouter();
  const { phase, source, fallbackToWebview } = useResolvedStream(url, player);
  const externalPlayer = useSettingsStore((s) => s.externalPlayer);
  const [forceInternal, setForceInternal] = useState(false);

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

  if (phase === 'checking' || phase === 'resolving') {
    return (
      <View style={[styles.container, styles.overlay]}>
        <StatusBar hidden />
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>
          {phase === 'resolving' ? 'Résolution du flux vidéo…' : 'Préparation…'}
        </Text>
      </View>
    );
  }

  if (phase === 'native' && source) {
    if (externalPlayer && !forceInternal) {
      return (
        <ExternalPlayerLauncher
          source={source}
          subtitle={subtitle}
          onFallback={() => setForceInternal(true)}
        />
      );
    }
    return <NativePlayer source={source} subtitle={subtitle} onFallback={fallbackToWebview} />;
  }

  return <WebPlayer url={url} subtitle={subtitle} />;
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: '#000' },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
  },
  loadingText: { color: Colors.textSecondary, marginTop: Spacing.md, fontSize: FontSize.sm },
  errorText: { color: Colors.text, marginTop: Spacing.md, fontSize: FontSize.md, textAlign: 'center', paddingHorizontal: Spacing.xl },
  errorActions: { flexDirection: 'row', gap: Spacing.sm, marginTop: Spacing.lg },
  errorBtn: {
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm,
    borderRadius: Radius.md, backgroundColor: Colors.primary,
  },
  errorBtnSecondary: { backgroundColor: 'rgba(255,255,255,0.15)' },
  errorBtnText: { color: Colors.text, fontWeight: '600', fontSize: FontSize.sm },
  tapZones: {
    ...StyleSheet.absoluteFillObject,
    flexDirection: 'row',
  },
  tapZone: { flex: 2 },
  tapZoneCenter: { flex: 1 },
  seekFlash: {
    position: 'absolute', top: '42%',
    alignItems: 'center', gap: 4,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: Radius.full,
    width: 72, height: 72, justifyContent: 'center',
  },
  seekFlashLeft:  { left: '18%' },
  seekFlashRight: { right: '18%' },
  seekFlashText: { color: Colors.text, fontSize: FontSize.xs, fontWeight: '700' },
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
  speedBtn: {
    paddingHorizontal: Spacing.sm, paddingVertical: 6,
    borderRadius: Radius.md, backgroundColor: 'rgba(255,255,255,0.15)',
  },
  speedBtnText: { color: Colors.text, fontSize: FontSize.sm, fontWeight: '700' },
  speedMenu: {
    position: 'absolute', right: Spacing.lg,
    backgroundColor: 'rgba(20,20,25,0.95)',
    borderRadius: Radius.md, paddingVertical: Spacing.xs,
    minWidth: 100,
  },
  speedOption: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm,
  },
  speedOptionText: { color: Colors.textSecondary, fontSize: FontSize.sm },
  speedOptionActive: { color: Colors.primary, fontWeight: '700' },
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
  progressThumbActive: {
    width: 19, height: 19, borderRadius: Radius.full, marginLeft: -9, top: -8,
  },
});
