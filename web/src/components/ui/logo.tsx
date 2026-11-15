import { cn } from "@/lib/utils"

interface LogoProps {
  className?: string
  tone?: "light" | "dark"
  compact?: boolean
}

export function Logo({ className, tone = "dark", compact = false }: LogoProps) {
  return (
    <a
      href="#top"
      aria-label="GreenVRP 首页"
      className={cn("group inline-flex items-center gap-2.5", className)}
    >
      <span className="relative grid h-9 w-9 place-items-center overflow-hidden rounded-[0.7rem] bg-lime text-ink transition-transform duration-500 group-hover:rotate-[-8deg]">
        <svg viewBox="0 0 40 40" className="h-6 w-6" aria-hidden="true">
          <path
            d="M8 29c7 0 7-18 24-18"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            className="opacity-90"
          />
          <circle cx="8" cy="29" r="3.2" fill="currentColor" />
          <circle cx="32" cy="11" r="3.2" fill="none" stroke="currentColor" strokeWidth="2.4" />
        </svg>
      </span>
      {!compact && (
        <span className="flex flex-col leading-none">
          <span
            className={cn(
              "font-serif text-[1.35rem] leading-none tracking-[-0.01em]",
              tone === "dark" ? "text-ink" : "text-cream",
            )}
          >
            GreenVRP
          </span>
          <span
            className={cn(
              "mt-1 font-mono text-[0.5rem] uppercase tracking-[0.32em]",
              tone === "dark" ? "text-ink/50" : "text-cream/50",
            )}
          >
            Engine
          </span>
        </span>
      )}
    </a>
  )
}
