import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated, Easing } from 'react-native';
import Svg, { Path, Polygon, Rect } from 'react-native-svg';

// Animated.createAnimatedComponent(...) depuis 'react-native' (pas Reanimated) —
// ce projet évite volontairement Reanimated ailleurs (cf. scan-reader/index.tsx :
// "fonctionne dans Expo Go sans Reanimated"). L'API Animated classique anime les
// props SVG (strokeDashoffset, opacity) tout aussi bien, sans ce risque.
const AnimatedPath = Animated.createAnimatedComponent(Path);
const AnimatedPolygon = Animated.createAnimatedComponent(Polygon);
const AnimatedRect = Animated.createAnimatedComponent(Rect);

// Couleurs de marque (identiques aux SVG icon/wordmark) — volontairement
// distinctes de la palette runtime de l'app : c'est un moment de branding figé.
const BRAND = {
  bg:     '#0E0C0A',
  cream:  '#F3EDE2',
  red:    '#C1352E',
  gold:   '#B08B2E',
  muted:  '#8B8680',
};

const ENSO_LENGTH = 900; // longueur approximative du trait de l'ensō, ajustée au path ci-dessous

type Props = {
  onFinish?: () => void;
};

export default function SplashScreen({ onFinish }: Props) {
  const strokeDashoffset = useRef(new Animated.Value(ENSO_LENGTH)).current;
  const triangleOpacity  = useRef(new Animated.Value(0)).current;
  const hankoOpacity     = useRef(new Animated.Value(0)).current;
  const wordAnimeOpacity = useRef(new Animated.Value(0)).current;
  const wordAnimeY       = useRef(new Animated.Value(10)).current;
  const wordSamaOpacity  = useRef(new Animated.Value(0)).current;
  const wordSamaY        = useRef(new Animated.Value(10)).current;
  const taglineOpacity   = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // 1. Le trait d'encre se dessine (coup de pinceau) — prop SVG, pas de native driver.
    Animated.timing(strokeDashoffset, {
      toValue: 0,
      duration: 1400,
      easing: Easing.bezier(0.65, 0, 0.35, 1),
      useNativeDriver: false,
    }).start();

    // 2. Le triangle play apparaît dans l'ouverture
    Animated.sequence([
      Animated.delay(1250),
      Animated.timing(triangleOpacity, { toValue: 1, duration: 500, useNativeDriver: false }),
    ]).start();

    // 3. Le petit sceau hanko
    Animated.sequence([
      Animated.delay(1600),
      Animated.timing(hankoOpacity, { toValue: 1, duration: 400, useNativeDriver: false }),
    ]).start();

    // 4. Le wordmark
    Animated.sequence([
      Animated.delay(1750),
      Animated.parallel([
        Animated.timing(wordAnimeOpacity, { toValue: 1, duration: 500, useNativeDriver: true }),
        Animated.timing(wordAnimeY,       { toValue: 0, duration: 500, useNativeDriver: true }),
      ]),
    ]).start();
    Animated.sequence([
      Animated.delay(1950),
      Animated.parallel([
        Animated.timing(wordSamaOpacity, { toValue: 1, duration: 500, useNativeDriver: true }),
        Animated.timing(wordSamaY,       { toValue: 0, duration: 500, useNativeDriver: true }),
      ]),
    ]).start();

    // 5. Le tagline, puis fin du splash
    Animated.sequence([
      Animated.delay(2250),
      Animated.timing(taglineOpacity, { toValue: 1, duration: 600, useNativeDriver: true }),
    ]).start(({ finished }) => {
      if (finished) onFinish?.();
    });
  }, []);

  return (
    <View style={styles.container}>
      <Svg width={220} height={190} viewBox="0 0 300 260">
        <AnimatedPath
          d="M 227.9,204.4 A 88,88 0 1 1 227.9,93.8"
          stroke={BRAND.red}
          strokeWidth={20}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={ENSO_LENGTH}
          strokeDashoffset={strokeDashoffset}
        />
        <AnimatedPolygon
          points="210,120 210,168 258,145"
          fill={BRAND.red}
          opacity={triangleOpacity}
        />
        <AnimatedRect
          x={235}
          y={200}
          width={16}
          height={16}
          rx={3}
          fill={BRAND.gold}
          opacity={hankoOpacity}
        />
      </Svg>

      <View style={styles.wordmarkRow}>
        <Animated.Text style={[styles.wordCream, { opacity: wordAnimeOpacity, transform: [{ translateY: wordAnimeY }] }]}>
          ANIME
        </Animated.Text>
        <Animated.Text style={[styles.wordRed, { opacity: wordSamaOpacity, transform: [{ translateY: wordSamaY }] }]}>
          SAMA
        </Animated.Text>
      </View>

      <Animated.Text style={[styles.tagline, { opacity: taglineOpacity }]}>
        Votre monde d'anime
      </Animated.Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: BRAND.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  wordmarkRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 28,
  },
  wordCream: {
    fontSize: 32,
    fontWeight: '700',
    letterSpacing: 3,
    color: BRAND.cream,
  },
  wordRed: {
    fontSize: 32,
    fontWeight: '700',
    letterSpacing: 3,
    color: BRAND.red,
  },
  tagline: {
    marginTop: 10,
    fontSize: 11,
    letterSpacing: 4,
    color: BRAND.muted,
    textTransform: 'uppercase',
  },
});
