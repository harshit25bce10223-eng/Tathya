import { createFileRoute } from "@tanstack/react-router"
import { BrandSplash } from "@/components/Common/BrandSplash"
export const Route = createFileRoute("/splash")({
  component: () => <BrandSplash preview />,
})
