import React, { useState, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  FlatList,
  Image,
  Animated,
  PanResponder,
  ActivityIndicator,
  StatusBar,
  useWindowDimensions,
  Modal,
  TouchableOpacity,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { WebView } from 'react-native-webview';
import { Colors, Spacing, FontSize, Radius } from '@/constants/colors';
import { useScanReaderStore } from '@/stores/scanReaderStore';
import { useDownloadStore } from '@/stores/downloadStore';
import { LecteurScan } from '@/types';

// ─── Page zoomable (PanResponder — fonctionne dans Expo Go sans Reanimated) ──

function ZoomablePageImage({
  uri,
  screenWidth,
  hasError,
  onError,
  onScrollChange,
}: {
  uri: string;
  screenWidth: number;
  hasError: boolean;
  onError: () => void;
  onScrollChange: (enabled: boolean) => void;
}) {
  const [imgHeight, setImgHeight] = useState(screenWidth * 1.4);
  const [loading, setLoading] = useState(true);
  const [isZoomed, setIsZoomed] = useState(false);

  // Animated values (RN Animated, pas Reanimated)
  const animScale = useRef(new Animated.Value(1)).current;
  const animX     = useRef(new Animated.Value(0)).current;
  const animY     = useRef(new Animated.Value(0)).current;

  // État mutable partagé dans les closures PanResponder
  const g = useRef({
    scale: 1,
    savedScale: 1,
    transX: 0,
    transY: 0,
    savedX: 0,
    savedY: 0,
    pinchDist: 0,
    zoomed: false,
  });

  const markZoomed = useCallback((v: boolean) => {
    g.current.zoomed = v;
    setIsZoomed(v);
    onScrollChange(!v);
  }, [onScrollChange]);

  const resetZoom = useCallback(() => {
    const gs = g.current;
    gs.scale = 1; gs.savedScale = 1;
    gs.transX = 0; gs.transY = 0;
    gs.savedX = 0; gs.savedY = 0;
    gs.pinchDist = 0;
    Animated.parallel([
      Animated.spring(animScale, { toValue: 1, useNativeDriver: true }),
      Animated.spring(animX,     { toValue: 0, useNativeDriver: true }),
      Animated.spring(animY,     { toValue: 0, useNativeDriver: true }),
    ]).start();
    markZoomed(false);
  }, [animScale, animX, animY, markZoomed]);

  const dist = (touches: any[]) => {
    const dx = touches[0].pageX - touches[1].pageX;
    const dy = touches[0].pageY - touches[1].pageY;
    return Math.sqrt(dx * dx + dy * dy);
  };

  const panResponder = useRef(
    PanResponder.create({
      // Capturer les touches : pinch (2 doigts) ou pan quand déjà zoomé
      onStartShouldSetPanResponder: (e) =>
        e.nativeEvent.touches.length === 2 || g.current.zoomed,
      onMoveShouldSetPanResponder: (e) =>
        e.nativeEvent.touches.length === 2 || g.current.zoomed,

      onPanResponderGrant: (e) => {
        const gs = g.current;
        const t = e.nativeEvent.touches;
        if (t.length === 2) gs.pinchDist = dist(t);
        gs.savedScale = gs.scale;
        gs.savedX = gs.transX;
        gs.savedY = gs.transY;
      },

      onPanResponderMove: (e, gestureState) => {
        const gs = g.current;
        const t  = e.nativeEvent.touches;

        if (t.length === 2) {
          // ── Pinch zoom ──
          const newDist = dist(t);
          if (gs.pinchDist > 0) {
            const ratio    = newDist / gs.pinchDist;
            const newScale = Math.min(Math.max(gs.scale * ratio, 1), 5);
            gs.scale = newScale;
            animScale.setValue(newScale);
            if (newScale > 1.05 && !gs.zoomed) {
              markZoomed(true);
            }
          }
          gs.pinchDist = newDist;
        } else if (gs.zoomed) {
          // ── Pan (doigt unique, quand zoomé) ──
          const maxX = (screenWidth * (gs.scale - 1)) / 2;
          const newX = Math.min(Math.max(gs.savedX + gestureState.dx, -maxX), maxX);
          const newY = gs.savedY + gestureState.dy;
          gs.transX = newX;
          gs.transY = newY;
          animX.setValue(newX);
          animY.setValue(newY);
        }
      },

      onPanResponderRelease: (_, gestureState) => {
        const gs = g.current;
        gs.pinchDist  = 0;
        gs.savedScale = gs.scale;
        gs.savedX     = gs.transX;
        gs.savedY     = gs.transY;

        if (gs.scale < 1.1) {
          resetZoom();
        } else if (!gs.zoomed) {
          markZoomed(true);
        }
      },
    })
  ).current;

  // Double tap pour zoomer/réinitialiser (uniquement visible quand non zoomé,
  // Pressable indépendant du PanResponder → pas de conflit)
  const tapCount = useRef(0);
  const tapTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleTap = useCallback(() => {
    tapCount.current++;
    if (tapTimer.current) clearTimeout(tapTimer.current);
    tapTimer.current = setTimeout(() => { tapCount.current = 0; }, 300);
    if (tapCount.current >= 2) {
      tapCount.current = 0;
      const target = 2.5;
      g.current.scale = target;
      g.current.savedScale = target;
      Animated.spring(animScale, { toValue: target, useNativeDriver: true }).start();
      markZoomed(true);
    }
  }, [animScale, markZoomed]);

  if (hasError) {
    return (
      <View style={[styles.pageError, { width: screenWidth, height: imgHeight }]}>
        <Ionicons name="image-outline" size={32} color={Colors.textMuted} />
        <Text style={styles.pageErrorText}>Erreur de chargement</Text>
      </View>
    );
  }

  return (
    <View style={{ width: screenWidth, height: imgHeight }}>
      {/* Vue avec handlers PanResponder */}
      <Animated.View
        {...panResponder.panHandlers}
        style={{ width: screenWidth, height: imgHeight, overflow: 'hidden' }}
      >
        <Animated.View
          style={[
            { width: screenWidth, height: imgHeight },
            { transform: [{ translateX: animX }, { translateY: animY }, { scale: animScale }] },
          ]}
        >
          {loading && (
            <View style={StyleSheet.absoluteFill}>
              <ActivityIndicator color={Colors.primary} style={{ flex: 1 }} />
            </View>
          )}
          <Image
            source={{ uri }}
            style={{ width: '100%', height: '100%' }}
            resizeMode="contain"
            onLoad={(e) => {
              const { width: iw, height: ih } = e.nativeEvent.source;
              if (iw > 0) setImgHeight((ih / iw) * screenWidth);
              setLoading(false);
            }}
            onError={onError}
          />
        </Animated.View>
      </Animated.View>

      {/* Double-tap pour zoomer (visible quand non zoomé — pas en conflit avec PanResponder) */}
      {!isZoomed && (
        <Pressable
          style={StyleSheet.absoluteFill}
          onPress={handleTap}
        />
      )}

      {/* Bouton reset (visible quand zoomé — au-dessus de la vue PanResponder) */}
      {isZoomed && (
        <TouchableOpacity style={styles.resetZoomBtn} onPress={resetZoom}>
          <Ionicons name="contract-outline" size={16} color={Colors.text} />
          <Text style={styles.resetZoomText}>Réinitialiser</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ─── Lecteur d'images (galerie de pages) ─────────────────────────────────────

function ImageReader({
  images,
  onBack,
  title,
}: {
  images: string[];
  onBack: () => void;
  title: string;
}) {
  const { width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const [currentPage, setCurrentPage] = useState(0);
  const [showUI, setShowUI] = useState(true);
  const [scrollEnabled, setScrollEnabled] = useState(true);
  const [loadErrors, setLoadErrors] = useState<Set<number>>(new Set());
  const uiTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const toggleUI = useCallback(() => {
    if (uiTimer.current) clearTimeout(uiTimer.current);
    setShowUI(true);
    uiTimer.current = setTimeout(() => setShowUI(false), 3000);
  }, []);

  const onViewableChanged = useRef(({ viewableItems }: any) => {
    if (viewableItems.length > 0) setCurrentPage(viewableItems[0].index ?? 0);
  });

  return (
    <View style={styles.container}>
      <StatusBar hidden />

      <FlatList
        data={images}
        keyExtractor={(_, i) => String(i)}
        pagingEnabled
        horizontal={false}
        showsVerticalScrollIndicator={false}
        scrollEnabled={scrollEnabled}
        onViewableItemsChanged={onViewableChanged.current}
        viewabilityConfig={{ itemVisiblePercentThreshold: 50 }}
        onScrollBeginDrag={toggleUI}
        renderItem={({ item: uri, index }) => (
          <ZoomablePageImage
            uri={uri}
            screenWidth={width}
            hasError={loadErrors.has(index)}
            onError={() => setLoadErrors((prev) => new Set([...prev, index]))}
            onScrollChange={setScrollEnabled}
          />
        )}
        ListEmptyComponent={
          <View style={styles.emptyPage}>
            <Ionicons name="image-outline" size={48} color={Colors.textMuted} />
            <Text style={styles.emptyText}>Aucune page disponible</Text>
          </View>
        }
      />

      {showUI && (
        <>
          <View style={[styles.topBar, { paddingTop: insets.top + Spacing.sm }]}>
            <Pressable style={styles.circleBtn} onPress={onBack}>
              <Ionicons name="chevron-back" size={22} color={Colors.text} />
            </Pressable>
            <Text style={styles.titleText} numberOfLines={1}>{title}</Text>
            <View style={styles.zoomTip}>
              <Ionicons name="expand-outline" size={14} color={Colors.textMuted} />
              <Text style={styles.zoomTipText}>Pincer pour zoomer</Text>
            </View>
          </View>

          <View style={[styles.pageIndicator, { bottom: insets.bottom + Spacing.md }]}>
            <Text style={styles.pageText}>{currentPage + 1} / {images.length}</Text>
          </View>
        </>
      )}
    </View>
  );
}

// ─── Lecteur WebView (lecteurs externes) ──────────────────────────────────────

function WebReader({
  lecteur,
  onBack,
  title,
}: {
  lecteur: LecteurScan;
  onBack: () => void;
  title: string;
}) {
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [showUI, setShowUI] = useState(true);
  const uiTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const toggleUI = () => {
    if (uiTimer.current) clearTimeout(uiTimer.current);
    setShowUI(true);
    uiTimer.current = setTimeout(() => setShowUI(false), 3000);
  };

  if (!lecteur.player_url) {
    return (
      <View style={[styles.container, styles.center]}>
        <Ionicons name="link-outline" size={48} color={Colors.textMuted} />
        <Text style={styles.emptyText}>URL du lecteur invalide</Text>
        <Pressable style={styles.backBtn} onPress={onBack}>
          <Text style={styles.backBtnText}>← Retour</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar hidden />
      <WebView
        source={{ uri: lecteur.player_url }}
        style={StyleSheet.absoluteFill}
        javaScriptEnabled
        domStorageEnabled
        allowsFullscreenVideo
        onLoadStart={() => setLoading(true)}
        onLoadEnd={() => setLoading(false)}
        onTouchStart={toggleUI}
        userAgent="Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
      />
      {loading && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Chargement du lecteur…</Text>
        </View>
      )}
      {showUI && (
        <View style={[styles.topBar, { paddingTop: insets.top + Spacing.sm }]}>
          <Pressable style={styles.circleBtn} onPress={onBack}>
            <Ionicons name="chevron-back" size={22} color={Colors.text} />
          </Pressable>
          <Text style={styles.titleText} numberOfLines={1}>{title}</Text>
        </View>
      )}
    </View>
  );
}

// ─── Modal choix lecteur ──────────────────────────────────────────────────────

function LecteurPicker({
  lecteurs,
  onSelect,
  onClose,
}: {
  lecteurs: LecteurScan[];
  onSelect: (l: LecteurScan) => void;
  onClose: () => void;
}) {
  return (
    <Modal transparent animationType="slide">
      <View style={pick.backdrop}>
        <View style={pick.sheet}>
          <Text style={pick.title}>Choisir un lecteur</Text>
          {lecteurs.map((l, i) => (
            <Pressable key={i} style={pick.row} onPress={() => onSelect(l)}>
              <Ionicons name="book-outline" size={20} color={Colors.primary} />
              <Text style={pick.lecteurName}>{l.lecteur || `Lecteur ${i + 1}`}</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.textMuted} />
            </Pressable>
          ))}
          <Pressable style={pick.cancelBtn} onPress={onClose}>
            <Text style={pick.cancelText}>Annuler</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function ScanReaderScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { chapitre, catalogueNom, catalogueSlug, scanNom, scanSlug, chapitreIndex, chapitres, goToNext, goToPrev } =
    useScanReaderStore();
  const getScanChapter = useDownloadStore((s) => s.getScanChapter);

  const [selectedLecteur, setSelectedLecteur] = useState<LecteurScan | null>(null);
  const [showLecteurPicker, setShowLecteurPicker] = useState(false);

  const handleBack = useCallback(() => {
    setSelectedLecteur(null);
    router.back();
  }, [router]);

  if (!chapitre) {
    return (
      <View style={[styles.container, styles.center]}>
        <Ionicons name="alert-circle" size={48} color={Colors.error} />
        <Text style={styles.emptyText}>Aucun chapitre sélectionné</Text>
        <Pressable style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backBtnText}>← Retour</Text>
        </Pressable>
      </View>
    );
  }

  // Vérifier si une version hors-ligne est disponible pour ce chapitre
  const localChapter = catalogueSlug && scanSlug
    ? getScanChapter(catalogueSlug, scanSlug, chapitre.numero)
    : undefined;
  const offlinePages = localChapter?.local_pages.filter(Boolean) ?? [];
  const isOffline    = offlinePages.length > 0;

  const title = `${catalogueNom} · ${scanNom} · Ch. ${chapitre.numero}${chapitre.titre ? ` — ${chapitre.titre}` : ''}`;
  // Priorité : pages locales → images réseau
  const images      = isOffline ? offlinePages : (chapitre.images ?? []);
  const hasImages   = images.length > 0;
  const hasLecteurs = !isOffline && chapitre.lecteurs && chapitre.lecteurs.length > 0;

  if (hasImages && !selectedLecteur) {
    return (
      <>
        <ImageReader
          images={images}
          onBack={handleBack}
          title={isOffline ? `${title} · 📥` : title}
        />
        <ChapitreNav
          onPrev={chapitreIndex > 0 ? goToPrev : undefined}
          onNext={chapitreIndex < chapitres.length - 1 ? goToNext : undefined}
          hasLecteurs={hasLecteurs}
          onOpenLecteurs={() => setShowLecteurPicker(true)}
          insets={insets}
        />
        {showLecteurPicker && (
          <LecteurPicker
            lecteurs={chapitre.lecteurs}
            onSelect={(l) => { setSelectedLecteur(l); setShowLecteurPicker(false); }}
            onClose={() => setShowLecteurPicker(false)}
          />
        )}
      </>
    );
  }

  if (selectedLecteur || (hasLecteurs && !hasImages)) {
    const lecteur = selectedLecteur ?? chapitre.lecteurs[0];
    if (chapitre.lecteurs.length > 1 && !selectedLecteur) setShowLecteurPicker(true);
    return (
      <>
        <WebReader lecteur={lecteur} onBack={() => setSelectedLecteur(null)} title={title} />
        <ChapitreNav
          onPrev={chapitreIndex > 0 ? goToPrev : undefined}
          onNext={chapitreIndex < chapitres.length - 1 ? goToNext : undefined}
          insets={insets}
        />
      </>
    );
  }

  return (
    <View style={[styles.container, styles.center, { paddingTop: insets.top }]}>
      <Ionicons name="book-outline" size={48} color={Colors.textMuted} />
      <Text style={styles.emptyText}>
        Ce chapitre n'a pas encore été synchronisé.{'\n'}
        Lancez une synchronisation depuis le panel admin.
      </Text>
      <Pressable style={styles.backBtn} onPress={handleBack}>
        <Text style={styles.backBtnText}>← Retour</Text>
      </Pressable>
    </View>
  );
}

// ─── Navigation entre chapitres ───────────────────────────────────────────────

function ChapitreNav({
  onPrev, onNext, hasLecteurs, onOpenLecteurs, insets,
}: {
  onPrev?: () => void;
  onNext?: () => void;
  hasLecteurs?: boolean;
  onOpenLecteurs?: () => void;
  insets: ReturnType<typeof useSafeAreaInsets>;
}) {
  return (
    <View style={[nav.bar, { paddingBottom: insets.bottom + Spacing.sm }]}>
      <Pressable style={[nav.btn, !onPrev && nav.btnDisabled]} onPress={onPrev} disabled={!onPrev}>
        <Ionicons name="chevron-back" size={20} color={onPrev ? Colors.text : Colors.textMuted} />
        <Text style={[nav.text, !onPrev && nav.textDisabled]}>Préc.</Text>
      </Pressable>

      {hasLecteurs && onOpenLecteurs && (
        <Pressable style={nav.lecteurBtn} onPress={onOpenLecteurs}>
          <Ionicons name="globe-outline" size={16} color={Colors.primary} />
          <Text style={nav.lecteurText}>Lecteurs</Text>
        </Pressable>
      )}

      <Pressable style={[nav.btn, !onNext && nav.btnDisabled]} onPress={onNext} disabled={!onNext}>
        <Text style={[nav.text, !onNext && nav.textDisabled]}>Suiv.</Text>
        <Ionicons name="chevron-forward" size={20} color={onNext ? Colors.text : Colors.textMuted} />
      </Pressable>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: '#111' },
  center:      { justifyContent: 'center', alignItems: 'center', gap: Spacing.md, padding: Spacing.lg },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
  },
  topBar: {
    position: 'absolute', top: 0, left: 0, right: 0,
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: Spacing.md, paddingBottom: Spacing.sm,
    backgroundColor: 'rgba(0,0,0,0.65)',
    gap: Spacing.sm,
  },
  circleBtn: {
    width: 38, height: 38, borderRadius: Radius.full,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center', alignItems: 'center',
  },
  titleText: { flex: 1, color: Colors.text, fontSize: FontSize.sm, fontWeight: '600' },
  zoomTip: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  zoomTipText: { color: Colors.textMuted, fontSize: 10 },
  pageIndicator: {
    position: 'absolute', alignSelf: 'center',
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: Spacing.md, paddingVertical: 4,
    borderRadius: Radius.full,
  },
  pageText:  { color: Colors.text, fontSize: FontSize.xs, fontWeight: '600' },
  emptyPage: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: Spacing.md },
  emptyText: { color: Colors.textMuted, fontSize: FontSize.md, textAlign: 'center', lineHeight: 22 },
  pageError: { justifyContent: 'center', alignItems: 'center', gap: Spacing.sm, backgroundColor: '#1a1a1a' },
  pageErrorText: { color: Colors.textMuted, fontSize: FontSize.xs },
  loadingText: { color: Colors.textSecondary, marginTop: Spacing.md, fontSize: FontSize.sm },
  backBtn: {
    marginTop: Spacing.md, paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.lg, backgroundColor: Colors.primary,
    borderRadius: Radius.full,
  },
  backBtnText: { color: Colors.text, fontWeight: '600' },
  resetZoomBtn: {
    position: 'absolute',
    bottom: Spacing.md,
    right: Spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    backgroundColor: 'rgba(0,0,0,0.7)',
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
  },
  resetZoomText: {
    color: Colors.text,
    fontSize: 11,
    fontWeight: '600',
  },
});

const nav = StyleSheet.create({
  bar: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(0,0,0,0.85)',
    paddingHorizontal: Spacing.lg, paddingTop: Spacing.sm,
  },
  btn:         { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: Spacing.sm, paddingHorizontal: Spacing.md },
  btnDisabled: { opacity: 0.35 },
  text:        { color: Colors.text, fontSize: FontSize.sm, fontWeight: '600' },
  textDisabled: { color: Colors.textMuted },
  lecteurBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: Colors.primary + '22', borderRadius: Radius.full,
    paddingVertical: Spacing.sm, paddingHorizontal: Spacing.md,
    borderWidth: 1, borderColor: Colors.primary,
  },
  lecteurText: { color: Colors.primary, fontSize: FontSize.sm, fontWeight: '600' },
});

const pick = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: Colors.card,
    borderTopLeftRadius: Radius.xl, borderTopRightRadius: Radius.xl,
    padding: Spacing.lg, gap: Spacing.sm,
  },
  title: { color: Colors.text, fontSize: FontSize.lg, fontWeight: '700', marginBottom: Spacing.sm },
  row: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  lecteurName: { flex: 1, color: Colors.text, fontSize: FontSize.md },
  cancelBtn: {
    marginTop: Spacing.md, paddingVertical: Spacing.md,
    alignItems: 'center', backgroundColor: Colors.surfaceAlt, borderRadius: Radius.md,
  },
  cancelText: { color: Colors.textMuted, fontWeight: '600' },
});
