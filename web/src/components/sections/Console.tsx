import { useState } from "react"
import { ArrowRight, Loader2, Settings2 } from "lucide-react"
import { RouteMap } from "@/components/visuals/RouteMap"
import { AnimatedNumber } from "@/components/ui/animated-number"
import { SectionHeading } from "@/components/ui/section-heading"
import { ParameterPanel } from "@/components/console/ParameterPanel"
import { useSolver } from "@/state/SolverProvider"
import { cn } from "@/lib/utils"

export function Console() {
  const {
    outcome,
    settings,
    vehicles,
    status,
    error,
    connection,
    runSolve,
    openConnect,
  } = useSolver()
  const [selectedRoute, setSelectedRoute] = useState<number | null>(
    outcome.solution.routes[0]?.vehicle_id ?? null,
  )
  const [progress, setProgress] = useState(0)

  const running = status === "running"
  const fleetTotal = Object.keys(vehicles).reduce(
    (sum, type) => sum + vehicles[type].count,
    0,
  )

  const activeRouteId = outcome.solution.routes.some(
    (route) => route.vehicle_id === selectedRoute,
  )
    ? selectedRoute
    : (outcome.solution.routes[0]?.vehicle_id ?? null)

  const handleRun = async () => {
    setProgress(4)
    const timer = window.setInterval(() => {
      setProgress((value) => (value >= 92 ? 92 : value + Math.max(1, (92 - value) * 0.07)))
    }, 180)
    const ok = await runSolve()
    window.clearInterval(timer)
    if (ok) {
      setProgress(100)
      window.setTimeout(() => setProgress(0), 1000)
      window.setTimeout(() => {
        document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" })
      }, 420)
    } else {
      setProgress(0)
    }
  }

  return (
    <section id="console" className="relative overflow-hidden bg-ink py-24 text-cream sm:py-32">
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute right-[-20%] top-[-15%] h-[42rem] w-[42rem] rounded-full bg-[radial-gradient(circle,hsl(var(--forest)/0.55),transparent_65%)] blur-3xl" />
        <svg viewBox="0 0 800 800" className="absolute -bottom-32 -left-40 h-[36rem] w-[36rem] opacity-50">
          {Array.from({ length: 11 }).map((_, index) => (
            <circle
              key={index}
              cx="400"
              cy="400"
              r={70 + index * 34}
              fill="none"
              stroke="hsl(var(--cream))"
              strokeOpacity={index % 3 === 0 ? 0.06 : 0.035}
            />
          ))}
        </svg>
      </div>

      <div className="container-x relative">
        <div className="grid items-end gap-10 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <SectionHeading
              tone="dark"
              index="02"
              eyebrow="Optimization console"
              title={
                <>
                  把约束交给引擎，
                  <br />
                  <span className="text-cream/45">把确定性留给团队。</span>
                </>
              }
              lead="调整经济参数与车队编成，重新求解。所有指标都来自同一份可解释的成本模型。"
            />
          </div>
          <div className="hidden border-l border-cream/15 pl-7 lg:col-span-5 lg:block">
            <p className="font-serif text-[1.6rem] leading-snug text-cream/80">
              “参数是这里唯一的输入。
              <br />
              剩下的，交给求解器。”
            </p>
            <p className="mt-4 font-mono text-[0.5625rem] uppercase tracking-[0.2em] text-cream/30">
              Deterministic · Explainable · Reproducible
            </p>
          </div>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-12">
          <div className="card-dark grain relative p-5 sm:p-7 lg:col-span-7">
            <div className="relative mb-7 flex flex-wrap items-center justify-between gap-3 border-b border-cream/10 pb-5">
              <div className="flex items-center gap-2.5">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    connection.mode === "api" ? "bg-lime" : "bg-amber",
                  )}
                />
                <span className="text-[0.8125rem] font-medium text-cream/85">
                  {connection.mode === "api" ? "真实引擎" : "本地演示解算"}
                </span>
                <span className="rounded-full border border-cream/15 px-2 py-0.5 font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-cream/40">
                  {connection.mode === "api" ? "FastAPI" : "Local demo"}
                </span>
              </div>
              <button
                type="button"
                onClick={openConnect}
                className="inline-flex items-center gap-1.5 rounded-full border border-cream/15 px-3 py-1.5 text-[0.6875rem] text-cream/55 transition-colors hover:border-lime/40 hover:text-lime"
              >
                <Settings2 className="h-3 w-3" />
                连接设置
              </button>
            </div>

            <ParameterPanel />

            <div className="mt-8">
              <button
                type="button"
                onClick={handleRun}
                disabled={running || fleetTotal === 0}
                className="btn-sheen group flex h-[3.25rem] w-full items-center justify-center gap-2 rounded-full bg-lime text-sm font-semibold text-ink shadow-[0_18px_50px_-18px_hsl(var(--lime)/0.65)] transition-all duration-300 hover:bg-lime-deep active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {running ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    正在搜索更轻的路径…
                  </>
                ) : (
                  <>
                    运行绿色优化
                    <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </button>
              <div className="mt-3 flex items-center justify-between font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-cream/30">
                <span>
                  {connection.mode === "api"
                    ? `OR-TOOLS 主解 ${settings.search_time_limit}s + 时变·载重·车队·多种子 ALNS`
                    : "演示解算 · 约 1 秒"}
                </span>
                <span>输出 · 路线 / 成本 / 碳排</span>
              </div>
              <div className="mt-3 h-px overflow-hidden bg-cream/10">
                <div
                  className="h-full bg-lime transition-[width] duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {error && (
              <div className="mt-5 rounded-xl border border-amber/35 bg-amber/10 px-4 py-3 text-[0.75rem] leading-relaxed text-cream/80" role="alert">
                {error}
                <button
                  type="button"
                  onClick={openConnect}
                  className="ml-2 underline decoration-amber/60 underline-offset-2 hover:text-lime"
                >
                  检查连接
                </button>
              </div>
            )}
          </div>

          <div className="space-y-4 self-start lg:sticky lg:top-24 lg:col-span-5">
            <div className="card-dark overflow-hidden">
              <div className="flex items-center justify-between border-b border-cream/10 px-5 py-4">
                <div>
                  <div className="eyebrow text-lime/70">Plan preview</div>
                  <div className="mt-1 text-[0.8125rem] text-cream/55">
                    {outcome.solution.routes.length} 条路线 · {outcome.customers.length - 1} 节点 · 点击高亮
                  </div>
                </div>
                <span className="font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-cream/45">
                  Abstract map
                </span>
              </div>
              <RouteMap
                routes={outcome.solution.routes}
                customers={outcome.customers}
                selectedRouteId={activeRouteId}
                onSelectRoute={setSelectedRoute}
                compact
              />
              <div className="flex flex-wrap gap-2 border-t border-cream/10 px-5 py-4">
                {outcome.solution.routes.map((route, index) => (
                  <button
                    key={route.vehicle_id}
                    type="button"
                    onClick={() => setSelectedRoute(route.vehicle_id)}
                    title={`${route.vehicle_type} · ${route.stops.length - 2} 站`}
                    className={cn(
                      "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[0.6875rem] transition-colors",
                      activeRouteId === route.vehicle_id
                        ? "border-lime/50 text-cream"
                        : "border-cream/10 text-cream/50 hover:border-cream/25",
                    )}
                  >
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ background: route.vehicle_color }}
                    />
                    R{index + 1}
                    <span className="font-mono text-[0.625rem] text-cream/50">
                      {route.distance_km.toFixed(1)} km
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 overflow-hidden rounded-2xl border border-cream/10 bg-cream/10">
              {[
                { label: "总成本", value: outcome.cost.total_cost, prefix: "¥", decimals: 0 },
                { label: "碳排放", value: outcome.cost.carbon_emission_kg, suffix: " kg", decimals: 1 },
                { label: "迟到", value: outcome.solution.total_late_minutes, suffix: " min", decimals: 0 },
              ].map((metric) => (
                <div key={metric.label} className="bg-ink-soft px-4 py-4">
                  <div className="eyebrow text-cream/55">{metric.label}</div>
                  <div className="mt-1.5 font-serif text-lg text-cream sm:text-xl">
                    <AnimatedNumber
                      value={metric.value}
                      prefix={metric.prefix}
                      suffix={metric.suffix}
                      decimals={metric.decimals}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-cream/10 px-4 py-3.5">
              <p className="text-[0.6875rem] leading-relaxed text-cream/55">
                {outcome.source === "demo"
                  ? "当前为本地演示解算：内置样例数据 + 贪心路径构造，用于展示界面交互，并非 OR-Tools 结果。"
                  : `已连接 ${connection.apiBase} · 结果由 FastAPI 与 OR-Tools 返回。`}
              </p>
              <button
                type="button"
                onClick={openConnect}
                className="mt-2 inline-flex items-center gap-1 text-[0.6875rem] font-medium text-lime/80 transition-colors hover:text-lime"
              >
                {outcome.source === "demo" ? "切换真实引擎" : "连接设置"}
                <ArrowRight className="h-3 w-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
