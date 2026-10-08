import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import { createRootRoute, HeadContent, Outlet } from "@tanstack/react-router"
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools"
import { BrandFilters } from "@/components/Common/BrandFilters"
import { BrandSplash } from "@/components/Common/BrandSplash"
import ErrorComponent from "@/components/Common/ErrorComponent"
import NotFound from "@/components/Common/NotFound"

export const Route = createRootRoute({
  component: () => (
    <>
      <HeadContent />
      <BrandFilters />
      <Outlet />
      <BrandSplash />
      {import.meta.env.DEV && (
        <TanStackRouterDevtools position="bottom-right" />
      )}
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </>
  ),
  notFoundComponent: () => <NotFound />,
  errorComponent: () => <ErrorComponent />,
})
