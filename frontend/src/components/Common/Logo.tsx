import { Link } from "@tanstack/react-router"
import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content = (
    <span className={cn("brand-lockup inline-flex", className)}>
      <span className="brand-mark">
        <img
          src="/assets/images/tathya-logo.png"
          alt=""
          className="original-brand-icon"
        />
      </span>
      {variant !== "icon" && (
        <span
          className={cn(
            "brand-word",
            variant === "responsive" && "group-data-[collapsible=icon]:hidden",
          )}
        >
          tathya<span>तथ्य · EVERY FACT, CHECKED</span>
        </span>
      )}
    </span>
  )
  return asLink ? (
    <Link to="/" aria-label="Tathya home">
      {content}
    </Link>
  ) : (
    content
  )
}
