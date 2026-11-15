import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface SectionHeadingProps {
  index: string
  eyebrow: string
  title: ReactNode
  lead?: ReactNode
  tone?: "light" | "dark"
  className?: string
  align?: "left" | "center"
}

export function SectionHeading({
  index,
  eyebrow,
  title,
  lead,
  tone = "light",
  className,
  align = "left",
}: SectionHeadingProps) {
  const dark = tone === "dark"
  return (
    <div className={cn(align === "center" && "mx-auto text-center", className)}>
      <div
        className={cn(
          "flex items-center gap-3",
          align === "center" && "justify-center",
        )}
      >
        <span
          className={cn(
            "eyebrow",
            dark ? "text-lime" : "text-forest",
          )}
        >
          {index} — {eyebrow}
        </span>
        <span className={cn("h-px w-10", dark ? "bg-cream/25" : "bg-ink/20")} />
      </div>
      <h2
        className={cn(
          "display mt-5 text-[clamp(2.15rem,4.6vw,4rem)] leading-[1.02]",
          dark ? "text-cream" : "text-ink",
        )}
      >
        {title}
      </h2>
      {lead && (
        <p
          className={cn(
            "mt-5 max-w-xl text-[0.9375rem] leading-relaxed",
            align === "center" && "mx-auto",
            dark ? "text-cream/70" : "text-ink/70",
          )}
        >
          {lead}
        </p>
      )}
    </div>
  )
}
