const ITEMS = [
  "碳感知优化",
  "CARBON-AWARE",
  "软时间窗",
  "HETEROGENEOUS FLEET",
  "五维成本",
  "OR-TOOLS",
  "2.63 KG CO₂ / L",
  "异构车队",
  "CARBON BUDGET",
  "可解释方案",
]

export function Ticker() {
  const track = [...ITEMS, ...ITEMS]
  return (
    <div className="relative overflow-hidden border-y border-ink/10 bg-lime py-3.5 text-ink">
      <div className="marquee-mask">
        <div className="marquee-track flex w-max animate-marquee items-center">
          {track.map((item, index) => (
            <span key={`${item}-${index}`} className="flex items-center whitespace-nowrap">
              <span className="px-6 font-mono text-[0.6875rem] uppercase tracking-[0.22em] sm:px-8">
                {item}
              </span>
              <span className="text-ink/35" aria-hidden="true">
                ✳
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
