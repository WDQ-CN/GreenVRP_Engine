import { ArrowRight, ArrowUpRight } from "lucide-react"
import { buttonVariants } from "@/components/ui/button"
import { Reveal } from "@/components/ui/reveal"
import { useSolver } from "@/state/SolverProvider"
import { formatKg } from "@/lib/format"

export function ClosingCta() {
  const { outcome, openConnect, connection } = useSolver()

  return (
    <section className="relative overflow-hidden bg-ink py-28 text-cream sm:py-36">
      <div className="absolute inset-0" aria-hidden="true">
        <div className="absolute left-1/2 top-1/2 h-[44rem] w-[44rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,hsl(var(--forest)/0.7),transparent_62%)] blur-3xl" />
        <svg viewBox="0 0 1200 640" className="absolute inset-0 h-full w-full opacity-60" preserveAspectRatio="xMidYMid slice">
          {[120, 210, 300].map((radius, index) => (
            <circle
              key={radius}
              cx="600"
              cy="320"
              r={radius}
              fill="none"
              stroke="hsl(var(--cream))"
              strokeOpacity={index === 0 ? 0.12 : 0.055}
              strokeDasharray={index === 1 ? "1 12" : undefined}
            />
          ))}
          <path
            id="closing-route"
            d="M 120 470 C 300 420, 360 250, 600 300 S 900 480, 1090 330"
            fill="none"
            stroke="hsl(var(--lime))"
            strokeOpacity="0.3"
            strokeWidth="1.4"
            strokeDasharray="3 12"
          />
          <circle r="4" fill="hsl(var(--lime))">
            <animateMotion
              dur="16s"
              repeatCount="indefinite"
              path="M 120 470 C 300 420, 360 250, 600 300 S 900 480, 1090 330"
            />
          </circle>
          {[{ x: 600, y: 300 }, { x: 120, y: 470 }, { x: 1090, y: 330 }].map((node) => (
            <circle key={`${node.x}`} cx={node.x} cy={node.y} r="3" fill="hsl(var(--cream))" fillOpacity="0.35" />
          ))}
        </svg>
        <div className="grain absolute inset-0 opacity-50" />
      </div>

      <div className="container-x relative text-center">
        <Reveal>
          <div className="eyebrow text-lime/70">Ready when you are</div>
          <h2 className="display mx-auto mt-6 max-w-4xl text-[clamp(2.9rem,7.2vw,6rem)] leading-[0.98]">
            出发之前，
            <br />
            先算清楚。
          </h2>
          <p className="mx-auto mt-6 max-w-lg text-[0.9375rem] leading-relaxed text-cream/55">
            当前示例方案：{outcome.solution.routes.length} 条路线 ·{" "}
            {formatKg(outcome.cost.carbon_emission_kg)} CO₂。换一组参数，看看还能轻多少。
          </p>
        </Reveal>

        <Reveal delay={120}>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a href="#console" className={`${buttonVariants({ variant: "lime", size: "lg" })} btn-sheen`}>
              打开优化控制台
              <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover/btn:translate-x-1" />
            </a>
            <button
              type="button"
              onClick={openConnect}
              className={buttonVariants({ variant: "glassDark", size: "lg" })}
            >
              {connection.mode === "api" ? "管理引擎连接" : "连接真实引擎"}
              <ArrowUpRight className="h-4 w-4" />
            </button>
          </div>
        </Reveal>

        <Reveal delay={200}>
          <div className="mx-auto mt-10 flex max-w-2xl flex-wrap items-center justify-center gap-x-6 gap-y-2 border-t border-cream/10 pt-6 font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-cream/30">
            <span>OR-Tools</span>
            <span>Soft time windows</span>
            <span>Mixed fleet</span>
            <span>Carbon-aware</span>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
