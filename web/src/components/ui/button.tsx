import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/btn inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full font-medium transition-all duration-300 [transition-timing-function:cubic-bezier(0.16,1,0.3,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lime/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ink disabled:pointer-events-none disabled:opacity-45 active:scale-[0.985]",
  {
    variants: {
      variant: {
        lime: "bg-lime text-ink shadow-[0_10px_30px_-12px_hsl(var(--lime)/0.55)] hover:bg-lime-deep hover:shadow-[0_16px_40px_-12px_hsl(var(--lime)/0.6)]",
        ink: "bg-ink text-cream hover:bg-forest",
        glassDark:
          "glass-dark text-cream hover:border-cream/25 hover:bg-cream/10",
        glassLight:
          "glass-light text-ink hover:border-ink/15 hover:bg-cream/90",
        outline:
          "border border-ink/20 bg-transparent text-ink hover:border-ink/50 hover:bg-ink/[0.04]",
        ghost: "text-ink/70 hover:text-ink",
      },
      size: {
        sm: "h-9 px-4 text-[0.8125rem]",
        md: "h-11 px-5 text-sm",
        lg: "h-[3.25rem] px-7 text-[0.9375rem]",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "lime",
      size: "md",
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />
  ),
)
Button.displayName = "Button"

export { Button, buttonVariants }
