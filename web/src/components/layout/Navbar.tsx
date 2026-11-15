import { useEffect, useState } from "react"
import { ArrowUpRight, Menu, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Logo } from "@/components/ui/logo"
import { useSolver } from "@/state/SolverProvider"

const LINKS = [
  { label: "引擎", href: "#engine" },
  { label: "控制台", href: "#console" },
  { label: "方案", href: "#results" },
  { label: "能力", href: "#capabilities" },
]

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const { connection, openConnect } = useSolver()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  useEffect(() => {
    if (!open) return
    const close = () => setOpen(false)
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false)
    }
    const onResize = () => {
      if (window.innerWidth >= 768) setOpen(false)
    }
    window.addEventListener("hashchange", close)
    window.addEventListener("keydown", onKey)
    window.addEventListener("resize", onResize)
    return () => {
      window.removeEventListener("hashchange", close)
      window.removeEventListener("keydown", onKey)
      window.removeEventListener("resize", onResize)
    }
  }, [open])

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-50 px-4 pt-4 md:pt-6">
      {open && (
        <div
          className="pointer-events-auto fixed inset-0 bg-ink/35 backdrop-blur-[2px] md:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}
      <div className="pointer-events-auto relative z-10 mx-auto max-w-6xl">
        <nav
          className={cn(
            "flex items-center justify-between gap-3 rounded-[1.1rem] border px-3.5 py-2.5 transition-all duration-500 md:px-5",
            scrolled
              ? "border-ink/10 bg-cream/95 shadow-[0_18px_50px_-24px_hsl(var(--ink)/0.45)] backdrop-blur-xl"
              : "border-cream/25 bg-cream/80 shadow-[0_12px_40px_-26px_hsl(var(--ink)/0.5)] backdrop-blur-xl",
          )}
        >
          <Logo />

          <div className="hidden items-center gap-7 md:flex">
            {LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="link-underline text-[0.8125rem] font-medium text-ink/70 transition-colors hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={openConnect}
              className="hidden items-center gap-1.5 rounded-full px-3 py-2 text-[0.75rem] font-medium text-ink/65 transition-colors hover:bg-ink/5 hover:text-ink lg:inline-flex"
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  connection.mode === "api" ? "bg-lime-deep" : "bg-amber",
                )}
              />
              {connection.mode === "api" ? "引擎在线" : "演示模式"}
            </button>
            <a
              href="#console"
              className="hidden items-center gap-2 rounded-full bg-ink px-4 py-2.5 text-[0.8125rem] font-medium text-cream transition-all duration-300 hover:bg-forest sm:inline-flex"
            >
              开始优化
              <ArrowUpRight className="h-3.5 w-3.5 transition-transform duration-300 group-hover:translate-x-0.5" />
            </a>
            <button
              type="button"
              aria-label={open ? "关闭菜单" : "打开菜单"}
              aria-expanded={open}
              onClick={() => setOpen((value) => !value)}
              className="grid h-9 w-9 place-items-center rounded-full text-ink transition-colors hover:bg-ink/5 md:hidden"
            >
              {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </nav>

        <div
          className={cn(
            "grid overflow-hidden rounded-[1.1rem] transition-all duration-500 md:hidden",
            open ? "mt-2 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
          )}
        >
          <div className="min-h-0">
            <div className="rounded-[1.1rem] border border-ink/10 bg-cream/95 p-4 shadow-soft backdrop-blur-xl">
              <div className="flex flex-col">
                {LINKS.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className="flex items-center justify-between border-b border-ink/5 py-3 text-sm font-medium text-ink/80 last:border-0"
                  >
                    {link.label}
                    <ArrowUpRight className="h-3.5 w-3.5 text-ink/35" />
                  </a>
                ))}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false)
                    openConnect()
                  }}
                  className="h-10 rounded-full border border-ink/15 text-[0.8125rem] font-medium text-ink"
                >
                  {connection.mode === "api" ? "引擎在线" : "连接引擎"}
                </button>
                <a
                  href="#console"
                  onClick={() => setOpen(false)}
                  className="grid h-10 place-items-center rounded-full bg-ink text-[0.8125rem] font-medium text-cream"
                >
                  开始优化
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
