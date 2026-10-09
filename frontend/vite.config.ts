import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

// https://vitejs.dev/config/
export default defineConfig({
  css: { postcss: { plugins: [] } },
  build: {
    outDir: "../backend/app/frontend",
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
    // Exclude test files from Vite's module graph
    {
      name: "exclude-tests",
      enforce: "pre",
      resolveId(source, importer) {
        if (source.includes("/tests/") || source.includes("\\tests\\")) {
          return { id: source, external: true }
        }
        if (importer && (importer.includes("/tests/") || importer.includes("\\tests\\"))) {
          return { id: source, external: true }
        }
      },
    },
  ],
  server: {
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      "/demo": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
    fs: {
      deny: ["tests/**"],
    },
  },
})