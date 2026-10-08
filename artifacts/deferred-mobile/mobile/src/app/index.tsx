import { CameraView, useCameraPermissions } from "expo-camera"
import { Link, useFocusEffect } from "expo-router"
import { useCallback, useRef, useState } from "react"
import { Image, Linking, Pressable, ScrollView, Text, View } from "react-native"
import { SafeAreaView } from "react-native-safe-area-context"
import { colors, styles } from "../components/theme"
import { useScans } from "../lib/scans"

export default function CaptureScreen() {
  const [permission, requestPermission] = useCameraPermissions()
  const camera = useRef<CameraView>(null)
  const [focused, setFocused] = useState(false)
  const [ready, setReady] = useState(false)
  useFocusEffect(
    useCallback(() => {
      setFocused(true)
      setReady(false)
      return () => {
        setFocused(false)
        setReady(false)
      }
    }, []),
  )
  const [started, setStarted] = useState(false)
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const [error, setError] = useState("")
  const { addCapture } = useScans()
  async function capture() {
    if (!camera.current || !ready || busy) return
    setBusy(true)
    setError("")
    try {
      const photo = await camera.current.takePictureAsync({ quality: 0.85 })
      if (photo) {
        setPreview(photo.uri)
      }
    } catch {
      setError("The photo could not be captured. Please try again.")
    } finally {
      setBusy(false)
    }
  }
  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView
        contentContainerStyle={{ flexGrow: 1, padding: 24, paddingBottom: 110 }}
      >
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Text
            style={{
              fontSize: 25,
              fontWeight: "600",
              color: colors.text,
              letterSpacing: -1,
            }}
          >
            tathya{" "}
            <Text style={{ fontSize: 13, color: colors.amber }}>तथ्य</Text>
          </Text>
          <Text style={styles.eyebrow}>SCAN</Text>
        </View>
        <Text style={styles.title}>Evidence, in focus.</Text>
        <Text style={styles.description}>
          Capture a clear page. Keep the details that matter.
        </Text>
        <View
          style={{
            flex: 1,
            minHeight: 260,
            borderWidth: 1,
            borderColor: colors.line,
            borderRadius: 18,
            overflow: "hidden",
            marginVertical: 24,
            backgroundColor: colors.card,
          }}
        >
          {started && permission?.granted && focused ? (
            <CameraView
              ref={camera}
              facing="back"
              style={{ flex: 1 }}
              onCameraReady={() => setReady(true)}
              onMountError={() => {
                setError("Camera unavailable. Check your device settings.")
                setStarted(false)
              }}
            />
          ) : (
            <View
              style={{
                flex: 1,
                alignItems: "center",
                justifyContent: "center",
                padding: 35,
              }}
            >
              <View
                style={{
                  width: 130,
                  height: 170,
                  borderWidth: 1,
                  borderColor: "#bdd7bb65",
                  borderRadius: 8,
                  padding: 20,
                  justifyContent: "center",
                }}
              >
                {[75, 55, 70, 45].map((width) => (
                  <View
                    key={width}
                    style={{
                      height: 2,
                      width,
                      backgroundColor: "#a6b7ab55",
                      marginVertical: 10,
                    }}
                  />
                ))}
              </View>
              <Text
                style={{ color: colors.muted, fontSize: 12, marginTop: 28 }}
              >
                Keep the whole page inside the frame.
              </Text>
            </View>
          )}
          {preview && (
            <Image
              source={{ uri: preview }}
              resizeMode="contain"
              style={{
                position: "absolute",
                inset: 0,
                backgroundColor: colors.card,
              }}
            />
          )}
        </View>
        {error ? (
          <Text style={styles.error} accessibilityRole="alert">
            {error}
          </Text>
        ) : null}
        {preview ? (
          <View style={{ gap: 10 }}>
            <Pressable
              accessibilityRole="button"
              style={styles.button}
              onPress={() => {
                addCapture(preview)
                setPreview(null)
                setStarted(false)
                setReady(false)
              }}
            >
              <Text style={styles.buttonText}>Keep capture</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              style={styles.outlineButton}
              onPress={() => {
                setPreview(null)
                setStarted(true)
              }}
            >
              <Text style={styles.outlineText}>Retake photo</Text>
            </Pressable>
          </View>
        ) : started ? (
          <Pressable
            accessibilityRole="button"
            style={[styles.button, { opacity: ready && !busy ? 1 : 0.5 }]}
            disabled={!ready || busy}
            onPress={capture}
          >
            <Text style={styles.buttonText}>
              {busy ? "Capturing…" : "Capture page"}
            </Text>
          </Pressable>
        ) : (
          <Pressable
            accessibilityRole="button"
            style={styles.button}
            onPress={async () => {
              setError("")
              if (!permission?.granted) {
                if (permission?.canAskAgain === false) {
                  await Linking.openSettings()
                  return
                }
                const granted = await requestPermission()
                if (!granted.granted) {
                  setError("Camera access is needed to capture a page.")
                  return
                }
              }
              setStarted(true)
            }}
          >
            <Text style={styles.buttonText}>Open camera</Text>
          </Pressable>
        )}
        <Text style={[styles.small, { textAlign: "center" }]}>
          Captures stay in this session. Use Tathya Submit for document
          verification.
        </Text>
        <Link
          href="/captures"
          style={{
            color: colors.accent,
            textAlign: "center",
            fontSize: 12,
            marginTop: 12,
          }}
        >
          View recent captures
        </Link>
      </ScrollView>
    </SafeAreaView>
  )
}
