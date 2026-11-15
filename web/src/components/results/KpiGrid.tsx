import { ArrowDownRight, ArrowUpRight, Leaf, Route, Truck, Wallet } from "lucide-react"
import { AnimatedNumber } from "@/components/ui/animated-number"
import { Reveal } from "@/components/ui/reveal"
import { formatPct, savingsPct } from "@/lib/format"
import type { SolveOutcome } from "@/lib/types"

export function KpiGrid({ outcome }: { outcome: SolveOutcome }) {
  const { cost, solution, baseline } = outcome
  const saved = savingsPct(cost.carbon_emission_kg, baseline.carbon_kg)
  const vehicles = Object.values(solution.vehicles_used).reduce<number>(
    (sum, count) => sum + (count ?? 0),
    0,
  )
  const late = solution.total_late_minutes

  const cards = [
    {
      label: "总成本",
      code: "COST",
      icon: Wallet,
      value: cost.total_cost,
      prefix: "¥",
      decimals: 0,
      sub: `运输 ${formatPct((cost.cost_breakdown["运输变动成本"] / Math.max(cost.total_cost, 1)) * 100)} · 人工 ${formatPct((cost.cost_breakdown["人工时间成本"] / Math.max(cost.total_cost, 1)) * 100)}`,
      positive: true,
    },
    {
      label: "碳排放",
      code: "CO₂",
      icon: Leaf,
      value: cost.carbon_emission_kg,
      suffix: " kg",
      decimals: 1,
      sub: `较单点直送基线 −${formatPct(saved)}`,
      positive: true,
    },
    {
      label: "总里程",
      code: "DIST",
      icon: Route,
      value: cost.total_distance_km,
      suffix: " km",
      decimals: 1,
      sub: `${solution.routes.length} 条路线 · ${cost.total_time_min.toFixed(0)} 分钟`,
      positive: true,
    },
    {
      label: "在途车辆",
      code: "FLEET",
      icon: Truck,
      value: vehicles,
      suffix: " 辆",
      decimals: 0,
      sub: late > 0 ? `迟到 ${late} 分钟` : "全部按时间窗送达",
      positive: late === 0,
    },
  ]

  return (
    <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card, index) => {
        const Icon = card.icon
        return (
          <Reveal key={card.label} delay={index * 80}>
            <div className="group relative h-full overflow-hidden rounded-[1.35rem] border border-ink/10 bg-cream p-5 transition-all duration-500 hover:-translate-y-1 hover:border-forest/25 hover:shadow-soft">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span className="grid h-7 w-7 place-items-center rounded-full bg-ink/[0.04] text-forest">
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <span className="text-[0.75rem] font-medium text-ink/65">{card.label}</span>
                </div>
                <span className="font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-ink/25">
                  {card.code}
                </span>
              </div>
              <div className="mt-5 font-serif text-[2.15rem] leading-none text-ink">
                <AnimatedNumber
                  value={card.value}
                  prefix={card.prefix}
                  suffix={card.suffix}
                  decimals={card.decimals}
                />
              </div>
              <div className="mt-3 flex items-center gap-1.5 text-[0.6875rem] text-ink/60">
                {card.positive ? (
                  <ArrowDownRight className="h-3 w-3 text-forest" />
                ) : (
                  <ArrowUpRight className="h-3 w-3 text-amber" />
                )}
                <span>{card.sub}</span>
              </div>
              <span className="absolute bottom-0 left-5 right-5 h-px bg-gradient-to-r from-transparent via-ink/10 to-transparent" />
            </div>
          </Reveal>
        )
      })}
    </div>
  )
}
