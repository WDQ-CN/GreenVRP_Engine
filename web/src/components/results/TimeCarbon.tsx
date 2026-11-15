import { useEffect, useState } from "react"
import { formatKg, formatNumber, savingsPct } from "@/lib/format"
import type { SolveOutcome } from "@/lib/types"

const TIME_PARTS = [
  { key: "driving_time_min", label: "行驶", color: "hsl(var(--lime))" },
  { key: "service_time_min", label: "服务", color: "hsl(var(--mint))" },
  { key: "waiting_time_min", label: "等待", color: "hsl(var(--amber))" },
] as const

export function TimeCarbon({ outcome }: { outcome: SolveOutcome }) {
  const { cost, baseline } = outcome
  const [mounted, setMounted] = useState(false)
  const totalTime = Math.max(cost.driving_time_min + cost.service_time_min + cost.waiting_time_min, 1)
  const maxCarbon = Math.max(cost.carbon_emission_kg, baseline.carbon_kg, 1)
  const saved = savingsPct(cost.carbon_emission_kg, baseline.carbon_kg)

  useEffect(() => {
    const timer = window.setTimeout(() => setMounted(true), 200)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <div className="card-paper flex h-full flex-col p-6">
      <div>
        <div className="eyebrow text-forest/55">Time & carbon</div>
        <h3 className="mt-2 font-serif text-[1.5rem] leading-tight text-ink">时间去哪儿了</h3>
      </div>

      <div className="mt-6">
        <div className="flex items-baseline justify-between">
          <span className="text-[0.6875rem] text-ink/60">全车队时间分解</span>
          <span className="font-mono text-[0.6875rem] text-ink/55">{formatNumber(cost.total_time_min)} min</span>
        </div>
        <div className="mt-3 flex h-2.5 gap-px overflow-hidden rounded-full bg-ink/[0.05]">
          {TIME_PARTS.map((part) => (
            <span
              key={part.key}
              className="block h-full transition-[width] duration-1000 ease-out"
              style={{
                width: mounted ? `${(cost[part.key] / totalTime) * 100}%` : "0%",
                background: part.color,
              }}
            />
          ))}
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2">
          {TIME_PARTS.map((part) => (
            <div key={part.key}>
              <div className="flex items-center gap-1.5 text-[0.625rem] text-ink/55">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: part.color }} />
                {part.label}
              </div>
              <div className="mt-1 font-mono text-[0.75rem] text-ink/70">
                {formatNumber(cost[part.key], 0)} min
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="hairline my-6" />

      <div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="eyebrow text-forest/55">Carbon delta</div>
            <div className="mt-2 text-[0.8125rem] text-ink/65">碳排对比</div>
          </div>
          <div className="rounded-full bg-lime px-2.5 py-1 font-mono text-[0.625rem] font-semibold text-ink">
            −{saved.toFixed(1)}%
          </div>
        </div>

        <div className="mt-5 space-y-4">
          <div>
            <div className="flex items-baseline justify-between text-[0.6875rem]">
              <span className="text-ink/65">当前方案</span>
              <span className="font-mono text-ink/80">{formatKg(cost.carbon_emission_kg)}</span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-ink/[0.05]">
              <div
                className="h-full rounded-full bg-lime-deep transition-[width] duration-1000 ease-out"
                style={{ width: mounted ? `${(cost.carbon_emission_kg / maxCarbon) * 100}%` : "0%" }}
              />
            </div>
          </div>
          <div>
            <div className="flex items-baseline justify-between text-[0.6875rem]">
              <span className="text-ink/55">单点直送基线</span>
              <span className="font-mono text-ink/55">{formatKg(baseline.carbon_kg)}</span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-ink/[0.05]">
              <div
                className="h-full rounded-full bg-moss/55 transition-[width] duration-1000 ease-out"
                style={{ width: mounted ? `${(baseline.carbon_kg / maxCarbon) * 100}%` : "0%" }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-auto border-t border-ink/10 pt-4 text-[0.6875rem] leading-relaxed text-ink/55">
        基线 = 每个客户单独往返直送，按同车型平均油耗估算，仅用于对比。
      </div>
    </div>
  )
}
