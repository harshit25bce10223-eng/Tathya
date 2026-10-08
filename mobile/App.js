import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import * as Notifications from 'expo-notifications';
import { useCameraPermissions } from 'expo-camera';

export default function App() {
  const [backendUrl, setBackendUrl] = useState('http://20.20.16.233:8000');
  const [healthStatus, setHealthStatus] = useState('Not tested');
  const [loading, setLoading] = useState(false);
  const [secureStoreStatus, setSecureStoreStatus] = useState('Checking...');
  const [permission, requestPermission] = useCameraPermissions();

  useEffect(() => {
    async function testSecureStore() {
      try {
        await SecureStore.setItemAsync('tathya_probe', 'ready_h0');
        const val = await SecureStore.getItemAsync('tathya_probe');
        setSecureStoreStatus(val === 'ready_h0' ? 'PASS (Secure storage working)' : 'FAIL');
      } catch (e) {
        setSecureStoreStatus('ERROR: ' + e.message);
      }
    }
    testSecureStore();
  }, []);

  const checkHealth = async () => {
    setLoading(true);
    setHealthStatus('Connecting...');
    try {
      const res = await fetch(`${backendUrl}/health`);
      if (res.ok) {
        const json = await res.json();
        setHealthStatus(`PASS: ${JSON.stringify(json)}`);
      } else {
        setHealthStatus(`HTTP Error: ${res.status}`);
      }
    } catch (e) {
      setHealthStatus(`FAIL: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Tathya Scan (तथ्य)</Text>
      <Text style={styles.subtitle}>Phase 0 Pre-Event Environment Smoke Test</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Backend Connectivity</Text>
        <TextInput
          style={styles.input}
          value={backendUrl}
          onChangeText={setBackendUrl}
          placeholder="http://<LAN_IP>:8000"
          autoCapitalize="none"
        />
        <TouchableOpacity style={styles.button} onPress={checkHealth}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Ping /health</Text>}
        </TouchableOpacity>
        <Text style={styles.statusText}>Status: {healthStatus}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Camera Permission (expo-camera)</Text>
        <Text style={styles.statusText}>
          Granted: {permission ? (permission.granted ? 'YES' : 'NO') : 'Determining...'}
        </Text>
        {!permission?.granted && (
          <TouchableOpacity style={styles.smallButton} onPress={requestPermission}>
            <Text style={styles.buttonText}>Grant Camera Permission</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Secure Storage (expo-secure-store)</Text>
        <Text style={styles.statusText}>{secureStoreStatus}</Text>
      </View>

      <StatusBar style="auto" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 24,
    paddingTop: 60,
    backgroundColor: '#f8fafc',
    minHeight: '100%',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#0f172a',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    marginBottom: 24,
  },
  card: {
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 5,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#334155',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
    backgroundColor: '#f1f5f9',
    fontSize: 14,
  },
  button: {
    backgroundColor: '#2563eb',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  smallButton: {
    backgroundColor: '#475569',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 14,
  },
  statusText: {
    marginTop: 8,
    fontSize: 13,
    color: '#475569',
  },
});
