import { useBlocker } from "@tanstack/react-router"

export function useUnsavedChanges(dirty: boolean) {
  useBlocker({
    shouldBlockFn: () => dirty && !window.confirm("You have unsaved changes. Leave this page and discard them?"),
    enableBeforeUnload: dirty,
  })
}
