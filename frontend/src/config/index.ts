/**
 * TATHYA Frontend Configuration
 * Centralized config for API base URL and other settings.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1"

export const config = {
  api: {
    baseUrl: API_BASE_URL,
  },
} as const
