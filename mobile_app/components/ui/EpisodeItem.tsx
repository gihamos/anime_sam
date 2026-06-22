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
  const hasVideos = episode.videos && episode.videos.length > 0;

  return (
    <View style={styles.container}>
      <Pressable style={styles.header} onPress={() => setExpanded(!expanded)}>
        <View style={styles.epInfo}>
          <Text style={styles.epNum}>Épisode {episode.numero}</Text>
          {episode.titre && (
            <Text style={styles.epTitle} numberOfLines={1}>{episode.titre}</Text>
          )}
        </View>
        <View style={styles.right}>
          {hasVideos && (
            <View style={styles.countBadge}>
              <Text style={styles.countText}>{episode.videos.length}</Text>
            </View>
          )}
          <Ionicons
            name={expanded ? 'chevron-up' : 'chevron-down'}
            size={16}
            color={Colors.textMuted}
          />
        </View>
      </Pressable>

      {expanded && (
        <View style={styles.videoList}>
          {!hasVideos ? (
            <Text style={styles.noVideos}>
              Aucun lecteur disponible — synchronisez d'abord cet anime.
            </Text>
          ) : (
            episode.videos.map((video, idx) => (
              <Pressable
                key={idx}
                style={styles.videoItem}
                onPress={() => onPlay(video, episode)}
              >
                <Ionicons name="play-circle" size={20} color={Colors.primary} />
                <Text style={styles.playerName}>{video.lecteur || `Lecteur ${idx + 1}`}</Text>
                <Ionicons name="chevron-forward" size={14} color={Colors.textMuted} />
              </Pressable>
            ))
          )}
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
  epInfo: { flex: 1 },
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
  countBadge: {
    backgroundColor: Colors.primary + '33',
    borderRadius: Radius.full,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  countText: {
    color: Colors.primary,
    fontSize: FontSize.xs,
    fontWeight: '700',
  },
  videoList: {
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    padding: Spacing.md,
    gap: Spacing.xs,
  },
  noVideos: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    fontStyle: 'italic',
  },
  videoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    gap: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  playerName: {
    flex: 1,
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
});
