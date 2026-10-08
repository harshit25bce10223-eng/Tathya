import { BlurView } from "expo-blur"
import { Tabs } from "expo-router"
import { StatusBar } from "expo-status-bar"
import { Platform, StyleSheet, View } from "react-native"
import { SafeAreaProvider } from "react-native-safe-area-context"
import { colors } from "../components/theme"
import { ScanProvider } from "../lib/scans"

export default function Layout() {
  return (
    <SafeAreaProvider>
      <ScanProvider>
        <StatusBar style="light" />
        <Tabs
          screenOptions={{
            headerShown: false,
            tabBarIcon: () => null,
            tabBarIconStyle: { display: "none" },
            tabBarLabelPosition: "beside-icon",
            tabBarActiveTintColor: colors.accent,
            tabBarInactiveTintColor: colors.muted,
            tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
            tabBarStyle: {
              position: "absolute",
              backgroundColor:
                Platform.OS === "android" ? "#1b2722" : "transparent",
              borderTopWidth: 0,
              borderRadius: 25,
              marginHorizontal: 22,
              marginBottom: 22,
              height: 64,
              paddingBottom: 9,
              paddingTop: 8,
              overflow: "hidden",
              borderWidth: 1,
              borderColor: "#7b9c7a40",
            },
            tabBarBackground: () =>
              Platform.OS === "android" ? (
                <View
                  style={[
                    StyleSheet.absoluteFill,
                    { backgroundColor: colors.card },
                  ]}
                />
              ) : (
                <BlurView
                  tint="dark"
                  intensity={60}
                  style={StyleSheet.absoluteFill}
                />
              ),
          }}
        >
          <Tabs.Screen name="index" options={{ title: "Capture" }} />
          <Tabs.Screen name="captures" options={{ title: "Recent" }} />
          <Tabs.Screen name="settings" options={{ title: "Connection" }} />
        </Tabs>
      </ScanProvider>
    </SafeAreaProvider>
  )
}
