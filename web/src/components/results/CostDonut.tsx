import { useEffect, useState } from "react"
import { AnimatedNumber } from "@/components/ui/animated-number"
import { COST_ROWS } from "@/lib/data"
import { formatCNY, formatPct } from "@/lib/format"
import type { CostResult } from "@/lib/types"

interface CostDonutProps {
  cost: CostResult
  totalDemand: number
}

const RADIUS = 66
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

const INSIGHTS: Record<string, string> = {
  运输变动成本: "优先关注总里程与油耗——缩短里程通常比压低油价更直接。",
  人工时间成本: "行驶与等待时间占主导；提高装载率能摊薄每单人工。",
  车辆固定成本: "每多启用一条路线，就多一份固定成本；合并路线是最直接的杠杆。",
  违约惩罚成本: "迟到罚金已在主导成本；检查时间窗设置与发车时刻。",
  碳排放成本: "碳价已成为主要成本项；比较不同车型的单位载重排放。",
}

export function CostDonut({ cost, totalDemand }: CostDonutProps) {
  const [mounted, setMounted] = useState(false)
  const total = Math.max(cost.total_cost, 1)

  useEffect(() => {
    const timer = window.setTimeout(() => setMounted(true), 180)
    return () => window.clearTimeout(timer)
  }, [])

  const segments = COST_ROWS.map((row, index) => {
    const value = cost.cost_breakdown[row.key] ?? 0
    const arc = (value / total) * CIRCUMFERENCE
    const offset = COST_ROWS.slice(0, index).reduce(
      (sum, previous) => sum + ((cost.cost_breakdown[previous.key] ?? 0) / total) * CIRCUMFERENCE,
      0,
    )
    return { ...row, value, arc, offset }
  })
  const top = segments.reduce((best, segment) => (segment.value > best.value ? segment : best), segments[0])
  const unitMetrics = [
    { label: "单公里成本", value: `¥${(cost.total_cost / Math.max(cost.total_distance_km, 1)).toFixed(1)}` },
    { label: "单件成本", value: `¥${(cost.total_cost / Math.max(totalDemand, 1)).toFixed(1)}` },
    { label: "碳成本占比", value: formatPct((cost.carbon_cost / total) * 100, 1) },
  ]

  return (
    <div className="card-paper flex h-full flex-col p-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="eyebrow text-forest/55">Cost mix</div>
          <h3 className="mt-2 font-serif text-[1.5rem] leading-tight text-ink">五维成本构成</h3>
        </div>
        <span className="rounded-full border border-ink/10 px-2.5 py-1 font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-ink/40">
          CNY
        </span>
      </div>

      <div className="mt-6 flex flex-col items-center gap-6 sm:flex-row sm:gap-7">
        <div className="relative h-[11.5rem] w-[11.5rem] shrink-0">
          <svg viewBox="0 0 180 180" className="h-full w-full -rotate-90" role="img" aria-label="五维成本构成环形图">
            <circle cx="90" cy="90" r={RADIUS} fill="none" stroke="hsl(var(--ink))" strokeOpacity="0.07" strokeWidth="20" />
            {segments.map((segment, index) =>
              segment.value > 0 ? (
                <circle
                  key={segment.key}
                  cx="90"
                  cy="90"
                  r={RADIUS}
                  fill="none"
                  stroke={segment.color}
                  strokeWidth="20"
                  strokeDasharray={mounted ? `${Math.max(segment.arc - 2.4, 0.5)} ${CIRCUMFERENCE}` : `0 ${CIRCUMFERENCE}`}
                  strokeDashoffset={-segment.offset}
                  style={{ transition: "stroke-dasharray 1.1s cubic-bezier(0.16,1,0.3,1)", transitionDelay: `${index * 70}ms` }}
                />
              ) : null,
            )}
          </svg>
          <div className="pointer-events-none absolute inset-0 grid place-items-center">
            <div className="text-center">
              <div className="eyebrow text-ink/35">Total</div>
              <div className="mt-1 font-serif text-[1.65rem] leading-none text-ink">
                <AnimatedNumber value={cost.total_cost} prefix="¥" />
              </div>
              <div className="mt-1.5 text-[0.625rem] text-ink/55">五维合计</div>
            </div>
          </div>
        </div>

        <div className="w-full space-y-2.5">
          {segments.map((segment) => (
            <div key={segment.key} className="flex items-center gap-2.5">
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: segment.color }} />
              <span className="min-w-0 flex-1 truncate text-[0.75rem] text-ink/70">{segment.key}</span>
              <span className="font-mono text-[0.6875rem] tabular-nums text-ink/75">{formatCNY(segment.value)}</span>
              <span className="w-9 text-right font-mono text-[0.625rem] tabular-nums text-ink/45">
                {formatPct((segment.value / total) * 100, 0)}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2 border-t border-ink/10 pt-4">
        {unitMetrics.map((metric) => (
          <div key={metric.label}>
            <div className="text-[0.625rem] text-ink/55">{metric.label}</div>
            <div className="mt-1 font-mono text-[0.8125rem] text-ink/80">{metric.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-forest/15 bg-lime/20 px-3.5 py-3">
        <div className="eyebrow text-forest/75">结构洞察</div>
        <p className="mt-1.5 text-[0.6875rem] leading-relaxed text-ink/75">
          {top.key} 占比最高（{formatPct((top.value / total) * 100, 0)}）。
          {INSIGHTS[top.key]}
        </p>
      </div>

      <div className="mt-5 border-t border-ink/10 pt-4 text-[0.6875rem] leading-relaxed text-ink/55">
        人工成本包含行驶、服务与等待时间；碳成本按当前碳价折算。
      </div>
    </div>
  )
}
