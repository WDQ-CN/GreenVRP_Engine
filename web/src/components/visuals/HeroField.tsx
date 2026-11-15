import { useReducedMotion } from "@/lib/use-reduced-motion"

const ROUTES = [
  {
    d: "M -120 700 C 220 640, 340 430, 600 470 S 980 620, 1180 385 S 1400 255, 1560 310",
    color: "hsl(var(--lime))",
    opacity: 0.38,
    dur: 22,
    begin: "0s",
  },
  {
    d: "M 140 940 C 280 760, 320 620, 540 592 S 920 650, 1100 505 S 1290 340, 1560 360",
    color: "hsl(var(--mint))",
    opacity: 0.26,
    dur: 27,
    begin: "-8s",
  },
  {
    d: "M 160 -60 C 360 180, 540 250, 710 212 S 990 90, 1210 228 S 1380 430, 1560 392",
    color: "hsl(var(--cream))",
    opacity: 0.16,
    dur: 32,
    begin: "-16s",
  },
]

const NODES = [
  { x: 600, y: 470, label: "39.90N" },
  { x: 1180, y: 385, label: "116.40E" },
  { x: 540, y: 592, label: "" },
  { x: 1100, y: 505, label: "" },
  { x: 710, y: 212, label: "" },
]

function contour(baseline: number, amplitude: number, seed: number): string {
  let d = `M -120 ${baseline}`
  for (let x = -60; x <= 1560; x += 60) {
    const y =
      baseline +
      Math.sin(x * 0.0038 + seed) * amplitude +
      Math.sin(x * 0.0102 + seed * 1.7) * amplitude * 0.42 +
      Math.sin(x * 0.021 + seed * 0.6) * amplitude * 0.16
    d += ` L ${x} ${y.toFixed(1)}`
  }
  return d
}

export function HeroField() {
  const reduced = useReducedMotion()

  return (
    <div aria-hidden="true" className="absolute inset-0 overflow-hidden">
      <div className="absolute inset-0" style={{ background: "var(--gradient-dawn)" }} />
      <div className="absolute left-1/2 top-[-22%] h-[70vw] w-[70vw] max-h-[880px] max-w-[880px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,hsl(var(--forest)/0.75),transparent_64%)] blur-3xl" />
      <div className="absolute right-[-12%] top-[16%] h-[34vw] w-[34vw] rounded-full bg-[radial-gradient(circle,hsl(var(--lime)/0.13),transparent_68%)] blur-3xl" />

      <svg
        viewBox="0 0 1440 900"
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 h-full w-full"
      >
        <defs>
          <filter id="hero-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="route-fade" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="hsl(var(--lime))" stopOpacity="0" />
            <stop offset="28%" stopColor="hsl(var(--lime))" stopOpacity="0.55" />
            <stop offset="72%" stopColor="hsl(var(--mint))" stopOpacity="0.45" />
            <stop offset="100%" stopColor="hsl(var(--mint))" stopOpacity="0" />
          </linearGradient>
        </defs>

        <g className="animate-drift">
          {Array.from({ length: 15 }).map((_, index) => (
            <path
              key={index}
              d={contour(120 + index * 58, 26 + (index % 5) * 11, index * 0.85)}
              fill="none"
              stroke={index % 4 === 0 ? "hsl(var(--lime))" : "hsl(var(--cream))"}
              strokeOpacity={index % 4 === 0 ? 0.09 : 0.055}
              strokeWidth={index % 5 === 0 ? 1.1 : 0.7}
            />
          ))}
        </g>

        <g stroke="hsl(var(--cream))" strokeOpacity="0.045" strokeWidth="0.7">
          {Array.from({ length: 13 }).map((_, index) => (
            <line key={`v${index}`} x1={index * 120} y1="0" x2={index * 120} y2="900" />
          ))}
          {Array.from({ length: 8 }).map((_, index) => (
            <line key={`h${index}`} x1="0" y1={index * 128} x2="1440" y2={index * 128} />
          ))}
        </g>

        <g className="origin-[72%_28%] animate-spin-slow" opacity="0.5">
          <circle cx="1080" cy="270" r="210" fill="none" stroke="hsl(var(--cream))" strokeOpacity="0.09" strokeDasharray="1 14" />
          <circle cx="1080" cy="270" r="150" fill="none" stroke="hsl(var(--cream))" strokeOpacity="0.06" />
          <circle cx="1080" cy="270" r="6" fill="hsl(var(--lime))" fillOpacity="0.55" />
        </g>

        {ROUTES.map((route, index) => (
          <g key={index}>
            <path d={route.d} fill="none" stroke={route.color} strokeOpacity={route.opacity * 0.5} strokeWidth="1.2" />
            <path
              d={route.d}
              fill="none"
              stroke="url(#route-fade)"
              strokeOpacity={route.opacity}
              strokeWidth="1.7"
              strokeDasharray="3 13"
              className="animate-flow"
              style={{ animationDuration: `${index === 0 ? 3 : 4.4}s` }}
            />
            {!reduced && (
              <circle r="3.2" fill={route.color} filter="url(#hero-glow)" opacity="0.9">
                <animateMotion dur={`${route.dur}s`} begin={route.begin} repeatCount="indefinite" path={route.d} />
              </circle>
            )}
          </g>
        ))}

        {NODES.map((node, index) => (
          <g key={index}>
            <circle cx={node.x} cy={node.y} r="14" fill="hsl(var(--lime))" fillOpacity="0.04" className="animate-pulse-soft" style={{ animationDelay: `${index * 0.7}s` }} />
            <circle cx={node.x} cy={node.y} r="4.2" fill="hsl(var(--ink))" stroke="hsl(var(--lime))" strokeWidth="1.4" />
            <circle cx={node.x} cy={node.y} r="1.5" fill="hsl(var(--lime))" />
            {node.label && (
              <text x={node.x + 14} y={node.y + 4} fill="hsl(var(--cream))" fillOpacity="0.34" fontSize="9" fontFamily="monospace" letterSpacing="2">
                {node.label}
              </text>
            )}
          </g>
        ))}
      </svg>

      <div className="absolute inset-0 bg-[linear-gradient(180deg,hsl(var(--ink)/0.66)_0%,transparent_26%,transparent_58%,hsl(var(--ink)/0.92)_100%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(120%_85%_at_50%_38%,transparent_35%,hsl(var(--ink)/0.6)_100%)]" />
      <div className="grain absolute inset-0" />
    </div>
  )
}
