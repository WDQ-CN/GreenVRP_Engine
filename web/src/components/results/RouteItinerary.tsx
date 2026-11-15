import { vehicleColor, vehicleLabel } from "@/lib/data"
import { formatClock, formatPct } from "@/lib/format"
import type { RoutePlan } from "@/lib/types"
import { cn } from "@/lib/utils"
import { useSolver } from "@/state/SolverProvider"

interface RouteItineraryProps {
  routes: RoutePlan[]
  selectedRouteId: number | null
  onSelect: (routeId: number) => void
}

export function RouteItinerary({ routes, selectedRouteId, onSelect }: RouteItineraryProps) {
  const { vehicles } = useSolver()
  const active = routes.find((route) => route.vehicle_id === selectedRouteId) ?? routes[0]
  if (!active) return null
  const color =
    active.vehicle_color ||
    vehicleColor(active.vehicle_type, vehicles[active.vehicle_type])
  const load = Math.min(100, (active.total_demand / Math.max(active.capacity, 1)) * 100)

  return (
    <div className="card-paper flex h-full min-w-0 flex-col p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="eyebrow text-forest/55">Itinerary</div>
          <h3 className="mt-2 font-serif text-[1.5rem] leading-tight text-ink">逐站行车清单</h3>
        </div>
        <span className="font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-ink/55">
          {vehicleLabel(active.vehicle_type, vehicles[active.vehicle_type])}
        </span>
      </div>

      <div className="no-scrollbar mt-5 flex min-w-0 gap-2 overflow-x-auto pb-1">
        {routes.map((route, index) => {
          const activeTab = route.vehicle_id === active.vehicle_id
          return (
            <button
              key={route.vehicle_id}
              type="button"
              onClick={() => onSelect(route.vehicle_id)}
              aria-pressed={activeTab}
              className={cn(
                "inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-1.5 text-[0.6875rem] font-medium transition-all duration-300",
                activeTab
                  ? "border-ink/20 bg-ink text-cream"
                  : "border-ink/10 text-ink/65 hover:border-ink/25 hover:text-ink",
              )}
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{
                  background:
                    route.vehicle_color ||
                    vehicleColor(
                      route.vehicle_type,
                      vehicles[route.vehicle_type],
                      index,
                    ),
                }}
              />
              R{index + 1}
              <span className={cn("font-mono text-[0.625rem]", activeTab ? "text-cream/55" : "text-ink/50")}>
                {route.distance_km.toFixed(1)} km
              </span>
            </button>
          )
        })}
      </div>

      <div className="mt-5 grid grid-cols-4 gap-2 rounded-xl border border-ink/10 bg-ink/[0.025] px-3 py-3">
        {[
          { label: "站点", value: `${active.stops.length - 2}` },
          { label: "载重", value: `${active.total_demand}/${active.capacity}` },
          { label: "里程", value: `${active.distance_km.toFixed(1)}` },
          { label: "迟到", value: `${active.late_minutes} min` },
        ].map((metric) => (
          <div key={metric.label}>
            <div className="text-[0.625rem] text-ink/55">{metric.label}</div>
            <div className="mt-0.5 font-mono text-[0.75rem] text-ink/80">{metric.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span className="h-1 flex-1 overflow-hidden rounded-full bg-ink/10">
          <span className="block h-full rounded-full transition-[width] duration-700" style={{ width: `${load}%`, background: color }} />
        </span>
        <span className="font-mono text-[0.5625rem] text-ink/55">装载 {formatPct(load, 0)}</span>
      </div>

      <ol className="itinerary-scroll mt-6 max-h-[540px] overflow-y-auto overscroll-contain pr-1">
        {active.stops.map((stop, index) => {
          const depot = stop.customer_id === 0 || stop.customer_id === null
          const last = index === active.stops.length - 1
          return (
            <li key={`${stop.customer_name}-${index}`} className="relative grid grid-cols-[2.9rem_1rem_1fr] gap-2.5 pb-4 last:pb-0">
              <span className="pt-0.5 text-right font-mono text-[0.625rem] tabular-nums text-ink/55">
                {stop.arrival_time !== undefined ? formatClock(stop.arrival_time) : "--:--"}
              </span>
              <span className="relative flex justify-center">
                {!last && <span className="absolute bottom-[-1rem] top-3 w-px bg-ink/10" />}
                <span
                  className={cn(
                    "relative z-10 mt-1 block h-2.5 w-2.5 rounded-full",
                    depot ? "bg-ink" : "border-2 bg-cream",
                  )}
                  style={depot ? undefined : { borderColor: color }}
                />
              </span>
              <div className="min-w-0 pb-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={cn("text-[0.8125rem]", depot ? "font-medium text-ink/80" : "text-ink/75")}>
                    {stop.customer_name}
                  </span>
                  {depot && (
                    <span className="rounded-full border border-ink/10 px-1.5 py-0.5 font-mono text-[0.5rem] uppercase tracking-[0.12em] text-ink/50">
                      Depot
                    </span>
                  )}
                  {stop.is_late && (
                    <span className="rounded-full bg-amber/15 px-1.5 py-0.5 text-[0.5625rem] text-ink/60">
                      迟到 {stop.late_minutes} min
                    </span>
                  )}
                </div>
                {!depot && (
                  <div className="mt-0.5 font-mono text-[0.5625rem] text-ink/55">
                    需求 {stop.demand} 件 · 服务 {stop.service_time} min
                    {stop.tw_latest !== undefined && ` · 窗至 ${formatClock(stop.tw_latest)}`}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
