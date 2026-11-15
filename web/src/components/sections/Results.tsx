import { useState } from "react"
import { Download, RefreshCw } from "lucide-react"
import { SectionHeading } from "@/components/ui/section-heading"
import { Reveal } from "@/components/ui/reveal"
import { RouteMap } from "@/components/visuals/RouteMap"
import { KpiGrid } from "@/components/results/KpiGrid"
import { CostDonut } from "@/components/results/CostDonut"
import { RouteItinerary } from "@/components/results/RouteItinerary"
import { TimeCarbon } from "@/components/results/TimeCarbon"
import { buttonVariants } from "@/components/ui/button"
import { useSolver } from "@/state/SolverProvider"
import { cn } from "@/lib/utils"

export function Results() {
  const { outcome } = useSolver()
  const [selectedRoute, setSelectedRoute] = useState<number | null>(
    outcome.solution.routes[0]?.vehicle_id ?? null,
  )

  const activeRouteId = outcome.solution.routes.some(
    (route) => route.vehicle_id === selectedRoute,
  )
    ? selectedRoute
    : (outcome.solution.routes[0]?.vehicle_id ?? null)

  const stamp = new Date(outcome.solvedAt)
  const time = stamp.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
  const planId = `GV-${stamp.getTime().toString().slice(-6)}`

  const exportPlan = () => {
    const payload = {
      plan_id: planId,
      source: outcome.source,
      solved_at: outcome.solvedAt,
      settings_note: outcome.note,
      solution: outcome.solution,
      cost: outcome.cost,
      baseline: outcome.baseline,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `${planId}-greenvrp-plan.json`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1500)
  }

  return (
    <section id="results" className="relative overflow-hidden bg-paper py-24 sm:py-32">
      <div className="pointer-events-none absolute right-0 top-20 h-96 w-96 rounded-full border border-ink/5" />
      <div className="container-x relative">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <Reveal className="max-w-2xl">
            <SectionHeading
              index="03"
              eyebrow="Optimized plan"
              title={
                <>
                  一份可以直接
                  <br />
                  开车的方案。
                </>
              }
              lead="从成本到碳排，从路线到时间窗，每一个数字都能回溯到同一份输入与同一套计算。"
            />
          </Reveal>

          <Reveal delay={120} className="flex flex-col items-start gap-4 lg:items-end">
            <div className="flex flex-wrap items-center gap-2 text-[0.6875rem] text-ink/60">
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  outcome.source === "api" ? "bg-forest" : "bg-amber",
                )}
              />
              <span>{outcome.source === "api" ? "真实引擎 · FastAPI" : "本地演示解算"}</span>
              <span className="text-ink/20">/</span>
              <span className="font-mono">{planId}</span>
              <span className="text-ink/20">/</span>
              <span className="font-mono">{time}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={exportPlan} className={buttonVariants({ variant: "outline", size: "sm" })}>
                <Download className="h-3.5 w-3.5" />
                导出 JSON
              </button>
              <a href="#console" className={buttonVariants({ variant: "ink", size: "sm" })}>
                <RefreshCw className="h-3.5 w-3.5" />
                重新优化
              </a>
            </div>
          </Reveal>
        </div>

        <div className="mt-12">
          <KpiGrid outcome={outcome} />
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-12">
          <Reveal delay={80} className="min-w-0 lg:col-span-7">
            <div className="card-dark h-full overflow-hidden">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-cream/10 px-5 py-4 sm:px-6">
                <div>
                  <div className="eyebrow text-lime/70">Route overview</div>
                  <h3 className="mt-1.5 font-serif text-[1.4rem] leading-tight text-cream">路线总览</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {outcome.solution.routes.map((route, index) => (
                    <button
                      key={route.vehicle_id}
                      type="button"
                      onClick={() => setSelectedRoute(route.vehicle_id)}
                      title={`${route.vehicle_type} · ${route.stops.length - 2} 站 · ${route.distance_km.toFixed(1)} km`}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[0.625rem] transition-colors",
                        activeRouteId === route.vehicle_id
                          ? "border-lime/45 text-cream"
                          : "border-cream/10 text-cream/55 hover:border-cream/25",
                      )}
                    >
                      <span className="h-1.5 w-1.5 rounded-full" style={{ background: route.vehicle_color }} />
                      R{index + 1}
                      <span
                        className={cn(
                          "hidden sm:inline",
                          activeRouteId === route.vehicle_id ? "text-cream/45" : "text-cream/30",
                        )}
                      >
                        {route.vehicle_type}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
              <RouteMap
                routes={outcome.solution.routes}
                customers={outcome.customers}
                selectedRouteId={activeRouteId}
                onSelectRoute={setSelectedRoute}
              />
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-cream/10 px-5 py-3.5 font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-cream/30 sm:px-6">
                <span>点击路线高亮 · 悬停站点看详情 · 抽象投影</span>
                <span>{outcome.solution.routes.length} routes · {outcome.customers.length - 1} stops · {outcome.cost.total_distance_km.toFixed(1)} km</span>
              </div>
            </div>
          </Reveal>

          <Reveal delay={160} className="min-w-0 lg:col-span-5">
            <CostDonut
              cost={outcome.cost}
              totalDemand={outcome.solution.routes.reduce((sum, route) => sum + route.total_demand, 0)}
            />
          </Reveal>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-12">
          <Reveal delay={80} className="min-w-0 lg:col-span-7">
            <RouteItinerary
              routes={outcome.solution.routes}
              selectedRouteId={activeRouteId}
              onSelect={setSelectedRoute}
            />
          </Reveal>
          <Reveal delay={160} className="min-w-0 lg:col-span-5">
            <TimeCarbon outcome={outcome} />
          </Reveal>
        </div>

        <p className="mt-6 max-w-3xl text-[0.6875rem] leading-relaxed text-ink/60">
          {outcome.source === "demo"
            ? "演示结果由浏览器内贪心路径构造生成，用来展示交互与成本模型，并非 OR-Tools 最优解。启动 FastAPI 并连接真实引擎后，可替换为实际求解结果。"
            : "结果由 GreenVRP FastAPI 服务返回；地图为经纬度抽象投影，不用于实际导航。"}
        </p>
      </div>
    </section>
  )
}
