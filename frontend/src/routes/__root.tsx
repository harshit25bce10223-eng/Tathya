import { createRootRoute, HeadContent, Outlet } from "@tanstack/react-router"
import { BrandSplash } from "@/components/Common/BrandSplash"
import ErrorComponent from "@/components/Common/ErrorComponent"
import NotFound from "@/components/Common/NotFound"

export const Route = createRootRoute({
  component: () => (
    <>
      <HeadContent />
      <Outlet />
      <BrandSplash />
    </>
  ),
  notFoundComponent: () => <NotFound />,
  errorComponent: () => <ErrorComponent />,
})
