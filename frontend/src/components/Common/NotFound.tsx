import { Link } from "@tanstack/react-router"
import { Logo } from "./Logo"
export default function NotFound() {
  return (
    <main className="standalone-state">
      <Logo asLink={false} />
      <span className="eyebrow">404 · PAGE NOT FOUND</span>
      <h1>This page could not be found.</h1>
      <p>Check the address or return to your workspace.</p>
      <Link to="/" className="primary-link">
        Return to workspace
      </Link>
    </main>
  )
}
