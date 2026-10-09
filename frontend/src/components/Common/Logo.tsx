import { Link } from "@tanstack/react-router"
import logoImage from "@/assets/brand/tathya-logo-v2.png"
import markImage from "@/assets/brand/tathya-mark-v2.png"
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
    <span
      className={cn("brand-lockup inline-flex", className)}
      role="img"
      aria-label="Tathya"
    >
      <img
        src={markImage}
        alt=""
        width={40}
        height={40}
        className={cn(
          "brand-icon-v2",
          variant === "full" && "hidden",
          variant === "responsive" &&
            "hidden group-data-[collapsible=icon]:block",
        )}
      />
      {variant !== "icon" && (
        <img
          src={logoImage}
          alt="Tathya — Every fact, checked"
          width={216}
          height={72}
          className={cn(
            "brand-logo-v2",
            variant === "responsive" && "group-data-[collapsible=icon]:hidden",
          )}
        />
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
