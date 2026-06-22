import React, { useState, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  Dimensions,
  Platform,
  StatusBar,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors, FontSize, Spacing, Radius } from '@/constants/colors';
import { Video as ExpoVideo, ResizeMode, AVPlaybackStatus } from 'expo-av';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

const { width, height } = Dimensions.get('window');

export default function PlayerScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { url, player, title, episode, saison } = useLocalSearchParams<{
    url: string;
    player: string;
    title?: string;
    episode?: string;
    saison?: string;
  }>();

  const videoRef = useRef<ExpoVideo>(null);
  const [status, setStatus] = useState<AVPlaybackStatus | null>(null);
  const [showControls, setShowControls] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const controlsTimer = useRef<ReturnType<typeof setTimeout>>();

  const isPlaying = status?.isLoaded && status.isPlaying;
  const isBuffering = status?.isLoaded && status.isBuffering;
  const isLoaded = status?.isLoaded;
  const position = status?.isLoaded ? status.positionMillis : 0;
  const duration = status?.isLoaded && status.durationMillis ? status.durationMillis : 0;

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
    if (isPlaying) {
      await videoRef.current.pauseAsync();
    } else {
      await videoRef.current.playAsync();
    }
    resetControlsTimer();
  };

  const seek = async (delta: number) => {
    if (!videoRef.current || !isLoaded) return;
    await videoRef.current.setPositionAsync(Math.max(0, position + delta * 1000));
    resetControlsTimer();
  };

  const progress = duration > 0 ? position / duration : 0;

  const subtitle = [
    title,
    saison ? `Saison ${saison}` : null,
    episode ? `Épisode ${episode}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <View style={styles.container}>
      <StatusBar hidden />

      <Pressable style={styles.videoWrapper} onPress={resetControlsTimer}>
        <ExpoVideo
          ref={videoRef}
          source={{ uri: url }}
          style={styles.video}
          resizeMode={ResizeMode.CONTAIN}
          shouldPlay
          onPlaybackStatusUpdate={setStatus}
          useNativeControls={false}
        />

        {/* Buffering indicator */}
        {isBuffering && (
          <View style={styles.bufferingOverlay}>
            <ActivityIndicator size="large" color={Colors.primary} />
          </View>
        )}

        {/* Controls overlay */}
        {showControls && (
          <View style={styles.controls}>
            {/* Top bar */}
            <View style={[styles.topBar, { paddingTop: insets.top + Spacing.sm }]}>
              <Pressable style={styles.backBtn} onPress={() => router.back()}>
                <Ionicons name="chevron-back" size={24} color={Colors.text} />
              </Pressable>
              <View style={styles.titleBlock}>
                <Text style={styles.titleText} numberOfLines={1}>{subtitle}</Text>
                {player && <Text style={styles.playerText}>{player}</Text>}
              </View>
            </View>

            {/* Center controls */}
            <View style={styles.centerControls}>
              <Pressable onPress={() => seek(-10)}>
                <View style={styles.seekBtn}>
                  <Ionicons name="play-back" size={28} color={Colors.text} />
                  <Text style={styles.seekLabel}>10s</Text>
                </View>
              </Pressable>

              <Pressable style={styles.playBtn} onPress={togglePlay}>
                <Ionicons
                  name={isPlaying ? 'pause' : 'play'}
                  size={40}
                  color={Colors.text}
                />
              </Pressable>

              <Pressable onPress={() => seek(10)}>
                <View style={styles.seekBtn}>
                  <Ionicons name="play-forward" size={28} color={Colors.text} />
                  <Text style={styles.seekLabel}>10s</Text>
                </View>
              </Pressable>
            </View>

            {/* Bottom bar */}
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

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  videoWrapper: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  video: {
    width,
    height,
  },
  bufferingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  controls: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'space-between',
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    gap: Spacing.md,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(255,255,255,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  titleBlock: { flex: 1 },
  titleText: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: '700',
  },
  playerText: {
    color: Colors.textSecondary,
    fontSize: FontSize.xs,
  },
  centerControls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.xxl,
  },
  seekBtn: {
    alignItems: 'center',
    gap: 4,
  },
  seekLabel: {
    color: Colors.textSecondary,
    fontSize: FontSize.xs,
  },
  playBtn: {
    width: 70,
    height: 70,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(124,106,247,0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bottomBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
  },
  timeText: {
    color: Colors.text,
    fontSize: FontSize.xs,
    fontVariant: ['tabular-nums'],
    minWidth: 42,
  },
  progressBar: {
    flex: 1,
    height: 3,
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: Radius.full,
    position: 'relative',
  },
  progressFill: {
    height: '100%',
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
  },
  progressThumb: {
    position: 'absolute',
    top: -5,
    width: 13,
    height: 13,
    borderRadius: Radius.full,
    backgroundColor: Colors.primary,
    marginLeft: -6,
  },
});
