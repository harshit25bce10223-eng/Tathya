/**
 * Tathya frontend configuration.
 *
 * VITE_API_BASE_URL should point to the FastAPI backend root (no trailing slash).
 * Example: http://20.20.16.233:8001
 *
 * Falls back to empty string so relative URLs work when frontend is served by FastAPI.
 */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

/** Convenience: full prefix for all v1 API calls */
export const API_V1 = `${API_BASE_URL}/api/v1`;
