import { AnimatedNumber } from "@/components/ui/animated-number"
import { COST_ROWS } from "@/lib/data"
import { formatCNY, formatNumber, formatPct, savingsPct } from "@/lib/format"
import { useSolver } from "@/state/SolverProvider"

export function LedgerVisual() {
  const { outcome, settings } = useSolver()
  const { cost, baseline, source } = outcome
  const saved = savingsPct(cost.carbon_emission_kg, baseline.carbon_kg)
  const maxRow = Math.max(...COST_ROWS.map((row) => cost.cost_breakdown[row.key] ?? 0), 1)

  return (
    <div className="relative">
      <div className="pointer-events-none absolute -left-6 -top-6 hidden h-24 w-24 rounded-full border border-ink/10 lg:block" />
      <div className="relative overflow-hidden rounded-[1.75rem] bg-ink p-6 text-cream shadow-lift sm:p-8">
        <div className="grain absolute inset-0 opacity-60" aria-hidden="true" />
        <div className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-[radial-gradient(circle,hsl(var(--lime)/0.18),transparent_65%)] blur-2xl" />

        <div className="relative flex items-start justify-between gap-4">
          <div>
            <div className="eyebrow text-lime/70">Carbon ledger</div>
            <div className="mt-2 text-[0.8125rem] text-cream/55">
              示例方案的碳账本 · {source === "demo" ? "本地演示" : "真实引擎"}
            </div>
          </div>
          <div className="rounded-full border border-cream/15 px-2.5 py-1 font-mono text-[0.625rem] uppercase tracking-[0.18em] text-cream/55">
            CO₂e
          </div>
        </div>

        <div className="relative mt-7 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="font-serif text-[clamp(2.8rem,5vw,4.2rem)] leading-none text-cream">
              <AnimatedNumber value={cost.carbon_emission_kg} decimals={1} />
              <span className="ml-2 text-base text-cream/55">kg</span>
            </div>
            <div className="mt-3 text-[0.75rem] text-cream/55">
              当前方案总碳排放 · 运输 + 服务 + 等待
            </div>
          </div>
          <div className="rounded-2xl border border-lime/25 bg-lime/10 px-4 py-2.5 text-right">
            <div className="eyebrow text-lime/70">vs 单点直送基线</div>
            <div className="mt-1 font-serif text-2xl leading-none text-lime">
              −<AnimatedNumber value={saved} decimals={1} suffix="%" />
            </div>
          </div>
        </div>

        <div className="relative mt-7 h-24 w-full">
          <svg viewBox="0 0 420 96" preserveAspectRatio="none" className="h-full w-full overflow-visible">
            <defs>
              <linearGradient id="ledger-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(var(--lime))" stopOpacity="0.28" />
                <stop offset="100%" stopColor="hsl(var(--lime))" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path
              d="M0 18 C 46 26, 58 62, 104 58 S 162 34, 208 46 S 270 78, 316 62 S 374 38, 420 30 L 420 96 L 0 96 Z"
              fill="url(#ledger-fill)"
            />
            <path
              d="M0 18 C 46 26, 58 62, 104 58 S 162 34, 208 46 S 270 78, 316 62 S 374 38, 420 30"
              fill="none"
              stroke="hsl(var(--lime))"
              strokeWidth="1.6"
              pathLength="1"
              className="route-draw"
              style={{ animationDuration: "2.2s" }}
            />
            <line x1="0" y1="86" x2="420" y2="86" stroke="hsl(var(--cream))" strokeOpacity="0.1" strokeDasharray="2 6" />
          </svg>
          <div className="absolute bottom-0 left-0 font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-cream/45">
            ↙ 优化后
          </div>
          <div className="absolute right-0 top-0 font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-cream/45">
            基线 {formatNumber(baseline.carbon_kg, 1)} kg
          </div>
        </div>

        <div className="relative mt-7 space-y-3.5 border-t border-cream/10 pt-6">
          <div className="flex items-center justify-between">
            <span className="eyebrow text-cream/55">五维成本构成</span>
            <span className="font-mono text-[0.6875rem] text-cream/55">{formatCNY(cost.total_cost)}</span>
          </div>
          {COST_ROWS.map((row) => {
            const value = cost.cost_breakdown[row.key] ?? 0
            return (
              <div key={row.key} className="grid grid-cols-[5.5rem_1fr_4.2rem] items-center gap-3">
                <span className="text-[0.6875rem] text-cream/55">{row.key.replace("成本", "")}</span>
                <span className="h-1 overflow-hidden rounded-full bg-cream/10">
                  <span
                    className="block h-full rounded-full transition-[width] duration-1000 ease-out"
                    style={{ width: `${Math.max(3, (value / maxRow) * 100)}%`, background: row.color }}
                  />
                </span>
                <span className="text-right font-mono text-[0.625rem] text-cream/50">
                  {formatPct((value / Math.max(cost.total_cost, 1)) * 100)}
                </span>
              </div>
            )
          })}
        </div>

        <div className="relative mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-cream/10 pt-4 font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-cream/30">
          <span>柴油 2.63 kg CO₂ / L</span>
          <span>碳价 ¥{settings.carbon_price.toFixed(2)} / kg</span>
        </div>
      </div>

      <div className="absolute -bottom-5 -left-3 hidden rotate-[-3deg] items-center gap-2 rounded-xl border border-ink/10 bg-cream px-4 py-3 text-ink shadow-soft sm:flex">
        <span className="grid h-7 w-7 place-items-center rounded-full bg-lime text-[0.6875rem] font-semibold">5</span>
        <span className="text-[0.75rem] font-medium">成本维度 · 全部可解释</span>
      </div>
    </div>
  )
}
