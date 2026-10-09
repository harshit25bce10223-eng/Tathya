export const apiOrigin = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "")
export function uploadAudit(body: FormData, signal?: AbortSignal, onProgress?: (percent: number) => void): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open("POST", `${apiOrigin}/api/v1/audits`)
    request.timeout = 120000
    const token = localStorage.getItem("access_token")
    if (token) request.setRequestHeader("Authorization", `Bearer ${token}`)
    const abort = () => request.abort()
    const cleanup = () => signal?.removeEventListener("abort", abort)
    request.upload.onprogress = event => {
      if (event.lengthComputable) onProgress?.(Math.round(100 * event.loaded / event.total))
    }
    request.onload = () => {
      cleanup()
      try {
        const result = JSON.parse(request.responseText)
        if (request.status >= 200 && request.status < 300) resolve(result)
        else reject(new ServiceError(request.status, typeof result.detail === "string" ? result.detail : "Upload could not be completed."))
      } catch { reject(new ServiceError(request.status, "The upload service returned an invalid response.")) }
    }
    request.onerror = () => { cleanup(); reject(new ServiceError(0, "Cannot reach the upload service. Check your connection and backend.")) }
    request.ontimeout = () => { cleanup(); reject(new ServiceError(0, "Upload timed out. Try fewer or smaller files.")) }
    request.onabort = () => { cleanup(); reject(new ServiceError(0, "Upload cancelled. If the server already received it, check your audit list before retrying.")) }
    signal?.addEventListener("abort", abort, { once: true })
    if (signal?.aborted) { cleanup(); reject(new ServiceError(0, "Upload cancelled.")); return }
    request.send(body)
  })
}
export class ServiceError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

export async function apiFetch(path: string, init: RequestInit = {}, authenticated = true) {
  const headers = new Headers(init.headers)
  const token = localStorage.getItem("access_token")
  if (authenticated && token) headers.set("Authorization", `Bearer ${token}`)
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 120000)
  const abort = () => controller.abort()
  init.signal?.addEventListener("abort", abort, { once: true })
  if (init.signal?.aborted) controller.abort()
  try {
    const response = await fetch(`${apiOrigin}/api/v1${path}`, { ...init, headers, signal: controller.signal })
    if (response.status === 401 && authenticated) {
      throw new ServiceError(401, "Your session expired. Sign in again to continue.")
    }
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      const details = body?.detail
      const message = typeof details === "string" ? details : Array.isArray(details)
        ? details.map((d: { msg?: string }) => d.msg ?? "Invalid input").join("; ")
        : `The service could not complete this request (${response.status}). Please try again.`
      throw new ServiceError(response.status, message)
    }
    // Keep the timeout active until the body has arrived, not only the headers.
    const body = response.status === 204 || response.status === 205 ? null : await response.arrayBuffer()
    return new Response(body, {status: response.status, statusText: response.statusText, headers: response.headers})
  } catch (error) {
    if (error instanceof ServiceError) throw error
    throw new ServiceError(0, controller.signal.aborted
      ? "The request timed out or was cancelled. Please try again."
      : "Cannot reach the service. Check your connection and that the backend is running.")
  } finally {
    window.clearTimeout(timer)
    init.signal?.removeEventListener("abort", abort)
  }
}
