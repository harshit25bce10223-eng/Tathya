import { Link } from "@tanstack/react-router"
import { Logo } from "./Logo"
export default function ErrorComponent() {
  return (
    <main className="standalone-state">
      <Logo asLink={false} />
      <span className="eyebrow">SOMETHING WENT WRONG</span>
      <h1>We couldn’t open this page.</h1>
      <p>
        Please try again. If the problem continues, return to your workspace.
      </p>
      <Link to="/" className="primary-link">
        Return to workspace
      </Link>
      <button
        className="back-link"
        type="button"
        onClick={() => window.location.reload()}
      >
        Try again
      </button>
    </main>
  )
}
