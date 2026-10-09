import { apiOrigin } from "@/api/transport"
/**
 * TATHYA Frontend Configuration
 * Centralized config for API base URL and other settings.
 */

const API_BASE_URL = `${apiOrigin}/api/v1`

export const config = {
  api: {
    baseUrl: API_BASE_URL,
  },
} as const
