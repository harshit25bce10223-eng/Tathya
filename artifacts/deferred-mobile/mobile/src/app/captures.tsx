import { Link } from "expo-router"
import { Image, Pressable, ScrollView, Text, View } from "react-native"
import { SafeAreaView } from "react-native-safe-area-context"
import { colors, styles } from "../components/theme"
import { useScans } from "../lib/scans"
export default function Captures() {
  const { captures, clearCaptures } = useScans()
  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.eyebrow}>YOUR SESSION</Text>
        <Text style={styles.title}>Recent captures.</Text>
        <Text style={styles.description}>
          A small record of the evidence you’ve brought into focus.
        </Text>
        {captures.length ? (
          captures.map((capture, index) => (
            <View key={capture.id} style={styles.card}>
              <Image
                source={{ uri: capture.uri }}
                style={{ height: 220, borderRadius: 8 }}
                resizeMode="contain"
              />
              <Text style={[styles.cardTitle, { marginTop: 16 }]}>
                Page {captures.length - index}
              </Text>
              <Text style={styles.small}>
                Captured{" "}
                {new Date(capture.capturedAt).toLocaleTimeString("en-IN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                · This session only
              </Text>
            </View>
          ))
        ) : (
          <View style={[styles.card, { paddingVertical: 45 }]}>
            <Text
              style={{
                color: colors.accent,
                fontSize: 38,
                textAlign: "center",
              }}
            >
              ＋
            </Text>
            <Text
              style={[styles.cardTitle, { textAlign: "center", marginTop: 18 }]}
            >
              Your first page starts here
            </Text>
            <Text
              style={[
                styles.description,
                { textAlign: "center", fontSize: 13 },
              ]}
            >
              Capture a clear document page to see it in this session.
            </Text>
            <Link
              href="/"
              style={{
                textAlign: "center",
                color: colors.accent,
                fontSize: 13,
                marginTop: 24,
              }}
            >
              Open capture
            </Link>
          </View>
        )}
        {captures.length > 0 && (
          <Pressable
            accessibilityRole="button"
            style={[styles.outlineButton, { marginTop: 24 }]}
            onPress={clearCaptures}
          >
            <Text style={styles.outlineText}>Clear session captures</Text>
          </Pressable>
        )}
        <Text style={styles.small}>
          Session captures are temporary. They are not uploaded or verified.
        </Text>
      </ScrollView>
    </SafeAreaView>
  )
}
