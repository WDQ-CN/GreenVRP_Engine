import { useMemo, useState, type KeyboardEvent } from "react"
import { createProjector, smoothPath } from "@/lib/geo"
import { formatClock } from "@/lib/format"
import { vehicleColor } from "@/lib/data"
import { useMediaQuery } from "@/lib/use-media-query"
import type { Customer, RoutePlan, Stop } from "@/lib/types"
import { cn } from "@/lib/utils"

interface RouteMapProps {
  routes: RoutePlan[]
  customers: Customer[]
  selectedRouteId: number | null
  onSelectRoute?: (routeId: number) => void
  className?: string
  compact?: boolean
}

const W = 800
const H = 520
const LABEL_FONT_SIZE = 10

interface LabelBox {
  x: number
  y: number
  width: number
  height: number
}

interface LabelPlacement {
  x: number
  y: number
  anchor: "start" | "middle" | "end"
}

interface RouteLabel extends LabelPlacement {
  stop: Stop
  index: number
  text: string
}

function estimateLabelWidth(text: string, fontSize: number): number {
  let units = 0
  for (const char of text) {
    if (/[\u4e00-\u9fff]/.test(char)) units += 1
    else if (char === " ") units += 0.32
    else if (char === "·" || char === ".") units += 0.36
    else units += 0.58
  }
  return units * fontSize
}

function labelBox(text: string, placement: LabelPlacement, fontSize: number): LabelBox {
  const width = estimateLabelWidth(text, fontSize)
  const left =
    placement.anchor === "start"
      ? placement.x
      : placement.anchor === "end"
        ? placement.x - width
        : placement.x - width / 2
  return {
    x: left - 6,
    y: placement.y - fontSize * 1.15,
    width: width + 12,
    height: fontSize * 1.6,
  }
}

function boxesOverlap(a: LabelBox, b: LabelBox): boolean {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y
  )
}

const DISTRICTS = [
  { label: "昌平", x: 210, y: 62 },
  { label: "顺义", x: 610, y: 92 },
  { label: "门头沟", x: 92, y: 250 },
  { label: "通州", x: 710, y: 290 },
  { label: "房山", x: 150, y: 440 },
  { label: "大兴", x: 520, y: 462 },
]

export function RouteMap({
  routes,
  customers,
  selectedRouteId,
  onSelectRoute,
  className,
  compact = false,
}: RouteMapProps) {
  const [hovered, setHovered] = useState<number | null>(null)
  const narrow = useMediaQuery("(max-width: 640px)")
  const labelFontSize = narrow ? 23 : LABEL_FONT_SIZE
  const depotLabelSize = narrow ? 20 : LABEL_FONT_SIZE
  const activeId = hovered ?? selectedRouteId
  const project = useMemo(() => createProjector(customers, W, H, 72), [customers])
  const depot = customers.find((customer) => customer.id === 0) ?? customers[0]
  const depotXY = project(depot)

  const geometry = useMemo(
    () =>
      routes.map((route) => {
        const xy = route.stops.map((stop) => project(stop))
        return { route, d: smoothPath(xy), points: xy }
      }),
    [routes, project],
  )

  const activeRoute = routes.find((route) => route.vehicle_id === activeId) ?? null
  const activeStops =
    activeRoute?.stops.filter((stop) => stop.customer_id !== null && stop.customer_id !== 0) ?? []
  const activeCustomers = new Set(
    activeStops.map((stop) => `${stop.lat.toFixed(4)},${stop.lon.toFixed(4)}`),
  )
  const labelStride = Math.max(1, Math.ceil(activeStops.length / 8))
  const labelStops = activeStops
    .map((stop, index) => ({ stop, index }))
    .filter(({ index }) => index % labelStride === 0 || index === activeStops.length - 1)
    .slice(0, 9)

  const labelLayout: RouteLabel[] = []
  if (!compact) {
    const occupied: LabelBox[] = [
      labelBox(depot.name, { x: depotXY.x + 24, y: depotXY.y + 4, anchor: "start" }, depotLabelSize),
    ]
    const scale = labelFontSize / LABEL_FONT_SIZE
    labelStops.forEach(({ stop, index }) => {
      const point = project(stop)
      const text = `${index + 1} · ${stop.customer_name}`
      const preferred = point.x < W * 0.52 ? "start" : "end"
      const other = preferred === "start" ? "end" : "start"
      const preferredOffset = (preferred === "start" ? 10 : -10) * scale
      const otherOffset = (other === "start" ? 10 : -10) * scale
      const candidates: LabelPlacement[] = [
        { x: point.x + preferredOffset, y: point.y - 7 * scale, anchor: preferred },
        { x: point.x + preferredOffset, y: point.y + 12 * scale, anchor: preferred },
        { x: point.x + preferredOffset, y: point.y - 23 * scale, anchor: preferred },
        { x: point.x + otherOffset, y: point.y - 7 * scale, anchor: other },
        { x: point.x + otherOffset, y: point.y + 12 * scale, anchor: other },
        { x: point.x + otherOffset, y: point.y - 23 * scale, anchor: other },
        { x: point.x, y: point.y - 12 * scale, anchor: "middle" },
        { x: point.x, y: point.y + 14 * scale, anchor: "middle" },
        { x: point.x, y: point.y - 28 * scale, anchor: "middle" },
      ]
      for (const candidate of candidates) {
        const box = labelBox(text, candidate, labelFontSize)
        if (occupied.some((existing) => boxesOverlap(existing, box))) continue
        occupied.push(box)
        labelLayout.push({ ...candidate, stop, index, text })
        break
      }
    })
  }

  const stopKey = (customer: Customer) => `${customer.lat.toFixed(4)},${customer.lon.toFixed(4)}`

  const handleKey = (event: KeyboardEvent<SVGGElement>, routeId: number) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      onSelectRoute?.(routeId)
    }
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="路线方案抽象地图，按经纬度投影"
      className={cn("h-auto w-full select-none", className)}
    >
      <defs>
        <pattern id="map-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="hsl(var(--cream))" strokeOpacity="0.045" strokeWidth="0.6" />
        </pattern>
        <filter id="map-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <radialGradient id="map-halo" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="hsl(var(--lime))" stopOpacity="0.1" />
          <stop offset="100%" stopColor="hsl(var(--lime))" stopOpacity="0" />
        </radialGradient>
      </defs>

      <rect width={W} height={H} fill="hsl(var(--ink))" />
      <rect width={W} height={H} fill="url(#map-grid)" />
      <circle cx={depotXY.x} cy={depotXY.y} r="220" fill="url(#map-halo)" />

      <g stroke="hsl(var(--cream))" fill="none" strokeOpacity="0.07">
        <ellipse cx={depotXY.x} cy={depotXY.y} rx="96" ry="78" />
        <ellipse cx={depotXY.x} cy={depotXY.y} rx="170" ry="132" strokeDasharray="2 8" />
        <ellipse cx={depotXY.x} cy={depotXY.y} rx="250" ry="196" strokeOpacity="0.045" />
        <path d="M -20 150 C 190 210, 380 120, 520 190 S 760 330, 840 300" strokeOpacity="0.06" />
        <path d="M 80 -20 C 210 130, 300 300, 520 330 S 700 360, 820 470" strokeOpacity="0.05" />
        <path d="M 720 -10 C 660 120, 700 240, 620 340 S 480 460, 500 540" strokeOpacity="0.05" />
      </g>
      <path
        d="M -20 420 C 140 390, 250 430, 380 410 S 660 350, 830 390"
        fill="none"
        stroke="hsl(var(--sky))"
        strokeOpacity="0.14"
        strokeWidth="1.4"
      />

      {!compact &&
        DISTRICTS.map((district) => (
          <text
            key={district.label}
            className="map-district"
            x={district.x}
            y={district.y}
            fill="hsl(var(--cream))"
            fillOpacity="0.22"
            fontSize="9"
            letterSpacing="3"
            fontFamily="'Noto Sans SC', sans-serif"
          >
            {district.label}
          </text>
        ))}

      <g className="map-compass">
        <text x="754" y="46" textAnchor="middle" fill="hsl(var(--cream))" fillOpacity="0.35" fontSize="9" fontFamily="monospace">
          N
        </text>
        <path d="M 754 54 L 754 78" stroke="hsl(var(--cream))" strokeOpacity="0.25" strokeWidth="1" />
        <path d="M 750 64 L 754 55 L 758 64" fill="none" stroke="hsl(var(--cream))" strokeOpacity="0.35" strokeWidth="1" />
      </g>

      {geometry.map(({ route, d }, index) => {
        const color = route.vehicle_color || vehicleColor(route.vehicle_type)
        const isActive = route.vehicle_id === activeId
        return (
          <g
            key={route.vehicle_id}
            role="button"
            tabIndex={0}
            aria-label={`路线 ${index + 1}，${route.vehicle_type}，${route.stops.length - 2} 站`}
            onClick={() => onSelectRoute?.(route.vehicle_id)}
            onKeyDown={(event) => handleKey(event, route.vehicle_id)}
            onMouseEnter={() => setHovered(route.vehicle_id)}
            onMouseLeave={() => setHovered(null)}
            className="cursor-pointer outline-none"
          >
            <path d={d} fill="none" stroke="transparent" strokeWidth="18" />
            {isActive && (
              <path d={d} fill="none" stroke={color} strokeOpacity="0.12" strokeWidth="9" strokeLinecap="round" />
            )}
            <path
              d={d}
              fill="none"
              stroke={color}
              strokeOpacity={isActive ? 0.9 : 0.32}
              strokeWidth={isActive ? 2.4 : 1.4}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="transition-all duration-300"
            />
            {isActive && (
              <path
                d={d}
                fill="none"
                stroke={color}
                strokeOpacity="0.85"
                strokeWidth="3.2"
                strokeLinecap="round"
                strokeDasharray="1 11"
                className="animate-flow"
              />
            )}
          </g>
        )
      })}

      {customers
        .filter((customer) => customer.id !== 0)
        .map((customer) => {
          const point = project(customer)
          const isOnActive = activeCustomers.has(stopKey(customer))
          return (
            <g key={customer.id} className="pointer-events-none">
              <circle
                cx={point.x}
                cy={point.y}
                r={isOnActive ? 5 : 3.2}
                fill={isOnActive ? "hsl(var(--ink))" : "hsl(var(--cream))"}
                fillOpacity={isOnActive ? 1 : 0.35}
                stroke={isOnActive ? "hsl(var(--lime))" : "none"}
                strokeWidth={isOnActive ? 1.6 : 0}
              />
              <title>{`${customer.name} · 需求 ${customer.demand} 件 · 时间窗 ${formatClock(customer.tw_earliest)}–${formatClock(customer.tw_latest)}`}</title>
            </g>
          )
        })}

      {labelLayout.map((label, slot) => (
        <g key={`${label.stop.customer_name}-${label.index}`} className="pointer-events-none">
          <text
            className="map-stop-name"
            data-slot={slot}
            x={label.x}
            y={label.y}
            textAnchor={label.anchor}
            fill="hsl(var(--cream))"
            fillOpacity="0.86"
            fontSize={labelFontSize}
            fontFamily="'Noto Sans SC', sans-serif"
          >
            {label.text}
          </text>
          <title>
            {`第 ${label.index + 1} 站 · ${label.stop.customer_name}${label.stop.arrival_time !== undefined ? ` · ${formatClock(label.stop.arrival_time)} 到达` : ""}`}
          </title>
        </g>
      ))}

      <g className="pointer-events-none">
        <circle cx={depotXY.x} cy={depotXY.y} r="20" fill="hsl(var(--lime))" fillOpacity="0.08" className="animate-pulse-soft" />
        <circle cx={depotXY.x} cy={depotXY.y} r="10" fill="hsl(var(--ink))" stroke="hsl(var(--lime))" strokeWidth="1.4" />
        <circle cx={depotXY.x} cy={depotXY.y} r="3" fill="hsl(var(--lime))" filter="url(#map-glow)" />
        <path d={`M ${depotXY.x - 18} ${depotXY.y} L ${depotXY.x - 10} ${depotXY.y} M ${depotXY.x + 10} ${depotXY.y} L ${depotXY.x + 18} ${depotXY.y} M ${depotXY.x} ${depotXY.y - 18} L ${depotXY.x} ${depotXY.y - 10} M ${depotXY.x} ${depotXY.y + 10} L ${depotXY.x} ${depotXY.y + 18}`} stroke="hsl(var(--lime))" strokeOpacity="0.55" strokeWidth="1" />
        <text className="map-depot-label" x={depotXY.x + 24} y={depotXY.y + 4} fill="hsl(var(--cream))" fillOpacity="0.75" fontSize="10" fontFamily="'Noto Sans SC', sans-serif">
          {depot.name}
        </text>
      </g>

      <g className="pointer-events-none">
        <line x1="52" y1="480" x2="108" y2="480" stroke="hsl(var(--cream))" strokeOpacity="0.35" strokeWidth="1" />
        <line x1="52" y1="476" x2="52" y2="484" stroke="hsl(var(--cream))" strokeOpacity="0.35" strokeWidth="1" />
        <line x1="108" y1="476" x2="108" y2="484" stroke="hsl(var(--cream))" strokeOpacity="0.35" strokeWidth="1" />
        <text className="map-scale" x="52" y="496" fill="hsl(var(--cream))" fillOpacity="0.3" fontSize="8" fontFamily="monospace" letterSpacing="1">
          5 KM · 抽象投影
        </text>
      </g>
    </svg>
  )
}
