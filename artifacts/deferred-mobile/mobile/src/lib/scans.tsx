import { createContext, type ReactNode, useContext, useState } from "react"
export interface Capture {
  id: string
  uri: string
  capturedAt: string
}
interface Session {
  captures: Capture[]
  addCapture: (uri: string) => void
  clearCaptures: () => void
}
const ScanContext = createContext<Session | null>(null)
export function ScanProvider({ children }: { children: ReactNode }) {
  const [captures, setCaptures] = useState<Capture[]>([])
  return (
    <ScanContext.Provider
      value={{
        captures,
        addCapture: (uri) =>
          setCaptures((current) => [
            {
              id: String(Date.now()),
              uri,
              capturedAt: new Date().toISOString(),
            },
            ...current,
          ]),
        clearCaptures: () => setCaptures([]),
      }}
    >
      {children}
    </ScanContext.Provider>
  )
}
export function useScans() {
  const context = useContext(ScanContext)
  if (!context) throw new Error("ScanProvider is required")
  return context
}
