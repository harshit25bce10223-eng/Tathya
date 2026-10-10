import type { InjectionCandidate } from "./phase6"

const prefix = "tathya-workspace:"
export function saveCandidate(auditId: string, candidate: InjectionCandidate) {
  sessionStorage.setItem(`${prefix}${auditId}`, JSON.stringify(candidate))
}
export function loadCandidate(auditId: string): InjectionCandidate | null {
  try { return JSON.parse(sessionStorage.getItem(`${prefix}${auditId}`) ?? "null") }
  catch { return null }
}
export function clearWorkspaceDrafts() {
  Object.keys(sessionStorage).filter(key => key.startsWith(prefix)).forEach(key => { sessionStorage.removeItem(key) })
}
