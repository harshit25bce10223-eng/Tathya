import * as SecureStore from "expo-secure-store"
import { useState } from "react"
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
} from "react-native"
import { SafeAreaView } from "react-native-safe-area-context"
import { colors, styles } from "../components/theme"
export default function Settings() {
  const [url, setUrl] = useState(
    process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000",
  )
  const [status, setStatus] = useState("Not connected")
  const [busy, setBusy] = useState(false)
  const [storage, setStorage] = useState("Not checked")
  async function connect() {
    setBusy(true)
    setStatus("Connecting…")
    try {
      const endpoint = new URL(url.trim())
      if (!["http:", "https:"].includes(endpoint.protocol))
        throw new Error("Use an HTTP or HTTPS address.")
      const response = await fetch(
        `${endpoint.toString().replace(/\/$/, "")}/health`,
        { signal: AbortSignal.timeout(10000) },
      )
      if (!response.ok) throw new Error(`Service returned ${response.status}`)
      setStatus("Connected · Service is reachable")
    } catch (error) {
      setStatus(
        error instanceof Error
          ? error.message
          : "Could not connect. Try again.",
      )
    } finally {
      setBusy(false)
    }
  }
  async function checkStorage() {
    if (Platform.OS === "web") {
      setStorage("Secure storage is available in the native app.")
      return
    }
    try {
      await SecureStore.setItemAsync("tathya_probe", "ready")
      const result = await SecureStore.getItemAsync("tathya_probe")
      await SecureStore.deleteItemAsync("tathya_probe")
      setStorage(
        result === "ready"
          ? "Secure storage is ready"
          : "Secure storage check failed",
      )
    } catch {
      setStorage("Secure storage is unavailable on this device.")
    }
  }
  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.eyebrow}>TATHYA SCAN</Text>
        <Text style={styles.title}>Stay connected.</Text>
        <Text style={styles.description}>
          Check the service connection before you begin.
        </Text>
        <Text style={styles.sectionLabel}>SERVICE ADDRESS</Text>
        <TextInput
          accessibilityLabel="Backend service address"
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          placeholder="https://your-tathya-service"
          placeholderTextColor={colors.muted}
          style={styles.input}
        />
        <Pressable
          accessibilityRole="button"
          style={styles.button}
          disabled={busy}
          onPress={connect}
        >
          {busy ? (
            <ActivityIndicator color={colors.background} />
          ) : (
            <Text style={styles.buttonText}>Check connection</Text>
          )}
        </Pressable>
        <Text style={styles.description} accessibilityLiveRegion="polite">
          {status}
        </Text>
        <Text style={styles.sectionLabel}>DEVICE READINESS</Text>
        <Text style={styles.description}>{storage}</Text>
        <Pressable
          accessibilityRole="button"
          style={[styles.outlineButton, { marginTop: 18 }]}
          onPress={checkStorage}
        >
          <Text style={styles.outlineText}>Check secure storage</Text>
        </Pressable>
        <Text style={[styles.small, { marginTop: 28 }]}>
          For a physical phone, use your service’s reachable network address.
          Localhost refers to the phone itself.
        </Text>
      </ScrollView>
    </SafeAreaView>
  )
}
