import type { ConfigContext, ExpoConfig } from 'expo/config';
export default ({ config }: ConfigContext): ExpoConfig => ({
 ...config, name: 'Tathya Scan', slug: config.slug || 'tathya-scan', scheme: 'tathya',
 ios: { ...config.ios, bundleIdentifier: 'ai.tathya.scan' },
 android: { ...config.android, package: 'ai.tathya.scan', blockedPermissions: ['android.permission.RECORD_AUDIO'] },
 web: { ...config.web, bundler: 'metro' },
 plugins: [...(config.plugins || []), ['expo-camera', { cameraPermission: 'Scan document images and Tathya passport QR codes.', recordAudioAndroid: false }], 'expo-notifications'],
});
