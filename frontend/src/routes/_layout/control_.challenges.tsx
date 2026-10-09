import { createFileRoute } from "@tanstack/react-router"
import { ChallengeLibrary } from "@/components/Phase6/ChallengeLibrary"
export const Route = createFileRoute("/_layout/control_/challenges")({
  component: ChallengeLibrary,
  head: () => ({ meta: [{ title: "Challenge Library - Tathya" }] }),
})