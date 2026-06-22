import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Radius, Spacing, FontSize } from '@/constants/colors';
import { Episode, Video } from '@/types';

interface Props {
  episode: Episode;
  onPlay: (video: Video, episode: Episode) => void;
}

export default function EpisodeItem({ episode, onPlay }: Props) {
  const [expanded, setExpanded] = React.useState(false);

  const groupedVideos = episode.videos.reduce<Record<string, Video[]>>((acc, v) => {
    const lang = v.langue || 'inconnu';
    if (!acc[lang]) acc[lang] = [];
    acc[lang].push(v);
    return acc;
  }, {});

  const langColors: Record<string, string> = {
    vf: Colors.vf,
    vostfr: Colors.vostfr,
    vo: Colors.vo,
  };

  return (
    <View style={styles.container}>
      <Pressable style={styles.header} onPress={() => setExpanded(!expanded)}>
        <View style={styles.epInfo}>
          <Text style={styles.epNum}>Épisode {episode.numero}</Text>
          {episode.titre && <Text style={styles.epTitle} numberOfLines={1}>{episode.titre}</Text>}
        </View>
        <View style={styles.right}>
          <View style={styles.langTags}>
            {Object.keys(groupedVideos).map((lang) => (
              <View key={lang} style={[styles.langTag, { backgroundColor: (langColors[lang] || Colors.primary) + '33' }]}>
                <Text style={[styles.langText, { color: langColors[lang] || Colors.primary }]}>
                  {lang.toUpperCase()}
                </Text>
              </View>
            ))}
          </View>
          <Ionicons
            name={expanded ? 'chevron-up' : 'chevron-down'}
            size={16}
            color={Colors.textMuted}
          />
        </View>
      </Pressable>

      {expanded && (
        <View style={styles.videoList}>
          {Object.entries(groupedVideos).map(([lang, videos]) => (
            <View key={lang}>
              <Text style={styles.langLabel}>{lang.toUpperCase()}</Text>
              {videos.map((video, idx) => (
                <Pressable
                  key={idx}
                  style={styles.videoItem}
                  onPress={() => onPlay(video, episode)}
                >
                  <Ionicons name="play-circle" size={20} color={langColors[lang] || Colors.primary} />
                  <Text style={styles.playerName}>{video.player}</Text>
                  <Ionicons name="chevron-forward" size={14} color={Colors.textMuted} />
                </Pressable>
              ))}
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    marginBottom: Spacing.sm,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.md,
    gap: Spacing.sm,
  },
  epInfo: {
    flex: 1,
  },
  epNum: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: '600',
  },
  epTitle: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    marginTop: 2,
  },
  right: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  langTags: {
    flexDirection: 'row',
    gap: 4,
  },
  langTag: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Radius.sm,
  },
  langText: {
    fontSize: 10,
    fontWeight: '700',
  },
  videoList: {
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    padding: Spacing.md,
    gap: Spacing.sm,
  },
  langLabel: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    fontWeight: '700',
    marginBottom: Spacing.xs,
    letterSpacing: 1,
  },
  videoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    gap: Spacing.sm,
  },
  playerName: {
    flex: 1,
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
});
