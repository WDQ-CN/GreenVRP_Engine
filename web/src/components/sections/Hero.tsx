import { useEffect, useRef } from "react"
import { ArrowDown, ArrowUpRight } from "lucide-react"
import { HeroField } from "@/components/visuals/HeroField"
import { buttonVariants } from "@/components/ui/button"
import { AnimatedNumber } from "@/components/ui/animated-number"
import { useSolver } from "@/state/SolverProvider"
import { useReducedMotion } from "@/lib/use-reduced-motion"

export function Hero() {
  const { outcome } = useSolver()
  const reduced = useReducedMotion()
  const fieldRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (reduced) return
    let frame = 0
    const onScroll = () => {
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        const node = fieldRef.current
        if (node) {
          const shift = Math.min(window.scrollY, 900) * 0.16
          node.style.transform = `translate3d(0, ${shift}px, 0) scale(1.04)`
        }
      })
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => {
      window.removeEventListener("scroll", onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [reduced])

  const routes = outcome.solution.routes.length

  return (
    <section id="top" className="relative isolate min-h-[100svh] overflow-hidden bg-ink text-cream">
      <div ref={fieldRef} className="absolute inset-0 will-change-transform">
        <HeroField />
      </div>

      <div className="relative z-10 flex min-h-[100svh] flex-col">
        <div className="container-x flex flex-1 flex-col items-center justify-center pb-8 pt-32 text-center sm:pt-36">
          <div className="animate-rise" style={{ animationDelay: "120ms" }}>
            <div className="glass-dark inline-flex items-center gap-2.5 rounded-full px-4 py-2">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-lime opacity-60" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-lime" />
              </span>
              <span className="text-[0.75rem] font-medium tracking-wide text-cream/80">
                碳感知路由 · OR-Tools 驱动
              </span>
            </div>
          </div>

          <h1
            className="display animate-rise mt-7 text-[clamp(3.1rem,8.2vw,7.4rem)] leading-[0.98] text-cream"
            style={{ animationDelay: "260ms" }}
          >
            <span className="block">让每一公里，</span>
            <span className="mt-1 block sm:mt-2">
              都
              <span className="relative inline-block text-lime">
                更轻一点
                <svg
                  aria-hidden="true"
                  viewBox="0 0 320 16"
                  preserveAspectRatio="none"
                  className="absolute -bottom-4 left-0 h-3 w-full overflow-visible"
                >
                  <path
                    d="M3 10 C 72 3, 216 3, 317 9"
                    fill="none"
                    stroke="hsl(var(--lime))"
                    strokeOpacity="0.8"
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    pathLength="1"
                    className="route-draw"
                    style={{ animationDelay: "1s", animationDuration: "1.4s" }}
                  />
                </svg>
              </span>
              。
            </span>
          </h1>

          <p
            className="animate-rise mt-7 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-cream/65 sm:text-base"
            style={{ animationDelay: "400ms" }}
          >
            把碳排放放进目标函数。在容量、软时间窗与异构车队的约束下，
            GreenVRP 为城市配送计算
            <span className="text-cream/90"> 更轻、更快、更省 </span>
            的可执行路径。
          </p>

          <div
            className="animate-rise mt-8 flex flex-col items-center gap-3 sm:flex-row"
            style={{ animationDelay: "520ms" }}
          >
            <a
              href="#console"
              className={`${buttonVariants({ variant: "lime", size: "lg" })} btn-sheen`}
            >
              开始优化
              <ArrowDown className="h-4 w-4 transition-transform duration-300 group-hover/btn:translate-y-0.5" />
            </a>
            <a
              href="#engine"
              className={buttonVariants({ variant: "glassDark", size: "lg" })}
            >
              读懂引擎
              <ArrowUpRight className="h-4 w-4 transition-transform duration-300 group-hover/btn:-translate-y-0.5 group-hover/btn:translate-x-0.5" />
            </a>
          </div>

          <div
            className="animate-rise mt-10 flex items-stretch gap-6 text-center sm:gap-10"
            style={{ animationDelay: "640ms" }}
          >
            {[
              { value: "5", unit: "维", label: "成本核算" },
              { value: "3", unit: "类", label: "异构车型" },
              { value: "5", unit: "组", label: "求解策略" },
            ].map((item, index) => (
              <div key={item.label} className="relative px-1 sm:px-2">
                {index > 0 && (
                  <span className="absolute -left-3 top-1/2 h-8 w-px -translate-y-1/2 bg-cream/15 sm:-left-5" />
                )}
                <div className="font-serif text-[2rem] leading-none text-cream sm:text-[2.4rem]">
                  {item.value}
                  <span className="ml-0.5 text-[0.9rem] text-lime">{item.unit}</span>
                </div>
                <div className="mt-2 text-[0.6875rem] tracking-wider text-cream/55">
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="container-x relative pb-6">
          <div
            className="animate-rise glass-dark grain relative overflow-hidden rounded-2xl px-4 py-4 sm:px-6"
            style={{ animationDelay: "760ms" }}
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3 text-left">
                <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-lime" />
                <div>
                  <div className="eyebrow text-lime/75">Live brief · 示例方案</div>
                  <div className="mt-1 flex items-center gap-2 text-[0.8125rem] text-cream/70">
                    北京城市配送 · {outcome.customers.length - 1} 节点
                    <span className="rounded-full border border-cream/15 px-2 py-0.5 text-[0.625rem] text-cream/55">
                      {outcome.source === "demo" ? "本地演示" : "真实引擎"}
                    </span>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-5 text-left sm:gap-10">
                <div>
                  <div className="eyebrow text-cream/55">总成本</div>
                  <div className="mt-1 font-serif text-xl text-cream sm:text-2xl">
                    <AnimatedNumber value={outcome.cost.total_cost} prefix="¥" />
                  </div>
                </div>
                <div>
                  <div className="eyebrow text-cream/55">碳排放</div>
                  <div className="mt-1 font-serif text-xl text-cream sm:text-2xl">
                    <AnimatedNumber value={outcome.cost.carbon_emission_kg} decimals={1} suffix=" kg" />
                  </div>
                </div>
                <div>
                  <div className="eyebrow text-cream/55">路线</div>
                  <div className="mt-1 font-serif text-xl text-cream sm:text-2xl">
                    <AnimatedNumber value={routes} suffix=" 条" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between font-mono text-[0.625rem] uppercase tracking-[0.2em] text-cream/30">
            <span className="hidden sm:inline">39.9042° N · 116.4074° E</span>
            <span className="flex items-center gap-2">
              Scroll to optimize
              <span className="relative h-8 w-px overflow-hidden bg-cream/15">
                <span className="absolute inset-x-0 top-0 h-3 animate-[float_2.4s_ease-in-out_infinite] bg-lime/70" />
              </span>
            </span>
            <span className="hidden sm:inline">GreenVRP / 02</span>
          </div>
        </div>
      </div>
    </section>
  )
}
