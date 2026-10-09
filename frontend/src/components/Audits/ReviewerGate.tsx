import { Link } from "@tanstack/react-router"
import type { ReactNode } from "react"
import { isReviewer } from "@/api/audits"
import useAuth from "@/hooks/useAuth"
export function ReviewerGate({ children }: { children: ReactNode }) {
  const { user, userError, retryUser } = useAuth()
  if (userError) return <div className="panel-state" role="alert"><h1>Could not check access</h1><p>{userError.message}</p><button className="primary-link" onClick={() => retryUser()}>Try again</button></div>
  if (!user)
    return (
      <div className="panel-state" role="status">
        Checking workspace access…
      </div>
    )
  if (!isReviewer(user))
    return (
      <div className="panel-state">
        <h1>Reviewer access required</h1>
        <p>Your audit results are available in the control center.</p>
        <Link to="/control" className="primary-link">
          View my audits
        </Link>
      </div>
    )
  return children
}
