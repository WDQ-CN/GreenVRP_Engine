import { useState, type MouseEvent } from "react"
import { Check, Copy, Gauge, Leaf, Timer, Truck } from "lucide-react"
import { Reveal } from "@/components/ui/reveal"
import { SectionHeading } from "@/components/ui/section-heading"

const CAPABILITIES = [
  {
    index: "01",
    icon: Leaf,
    title: "碳排入目标函数",
    body: "每一升柴油折合 2.63 kg CO₂，碳价直接进入成本。减排从 ESG 叙事，变成可以优化的数字。",
    detail: "kg CO₂ × 碳价 → 成本项",
  },
  {
    index: "02",
    icon: Timer,
    title: "软时间窗",
    body: "允许迟到，但把迟到分钟数转化为罚金。方案不会因为一个不可行窗口而整体失效。",
    detail: "迟到 1 分钟 = 可配置罚金",
  },
  {
    index: "03",
    icon: Truck,
    title: "异构车队混编",
    body: "4.2m / 7.6m / 9.6m 三种车型共享同一套约束，容量、油耗与速度分别参与计算。",
    detail: "3 类车型 · 不同载重与油耗",
  },
  {
    index: "04",
    icon: Gauge,
    title: "策略矩阵",
    body: "5 组首解策略与局部搜索组合，在时间预算内并行探索，返回搜索到的最优可行解。",
    detail: "5 组策略 · 可并行执行",
  },
]

const SNIPPET = `POST /api/v1/solve
X-API-Key: ••••••••

{
  "customers": [ ...13 nodes ],
  "params": {
    "carbon_price": 0.08,
    "search_time_limit": 45
  }
}`

function SpotlightCard({
  item,
  delay,
}: {
  item: (typeof CAPABILITIES)[number]
  delay: number
}) {
  const Icon = item.icon
  const move = (event: MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    event.currentTarget.style.setProperty("--mx", `${event.clientX - rect.left}px`)
    event.currentTarget.style.setProperty("--my", `${event.clientY - rect.top}px`)
  }

  return (
    <Reveal delay={delay} className="h-full">
      <div
        onMouseMove={move}
        className="spotlight-card group flex h-full flex-col rounded-[1.35rem] border border-ink/10 bg-cream p-6 transition-all duration-500 hover:-translate-y-1 hover:border-forest/25 hover:shadow-soft"
      >
        <div className="flex items-center justify-between">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-ink/[0.04] text-forest transition-colors duration-500 group-hover:bg-lime group-hover:text-ink">
            <Icon className="h-4 w-4" />
          </span>
          <span className="font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-ink/25">
            {item.index}
          </span>
        </div>
        <h3 className="mt-6 font-serif text-[1.35rem] leading-tight text-ink">{item.title}</h3>
        <p className="mt-3 text-[0.8125rem] leading-relaxed text-ink/65">{item.body}</p>
        <div className="mt-auto flex items-center gap-2 border-t border-ink/10 pt-4 font-mono text-[0.5625rem] uppercase tracking-[0.12em] text-ink/55">
          <span className="h-1 w-1 rounded-full bg-lime-deep" />
          {item.detail}
        </div>
      </div>
    </Reveal>
  )
}

export function Capabilities() {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(SNIPPET)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section id="capabilities" className="relative overflow-hidden bg-paper py-24 sm:py-32">
      <div className="container-x">
        <Reveal>
          <SectionHeading
            index="04"
            eyebrow="Capabilities"
            title={
              <>
                不只是更短的
                <br />
                路线。
              </>
            }
            lead="四组能力，共用一份成本模型。每一次求解，都能讲清楚钱花在哪、碳排在哪。"
          />
        </Reveal>

        <div className="mt-12 grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
          {CAPABILITIES.map((item, index) => (
            <SpotlightCard key={item.index} item={item} delay={index * 80} />
          ))}
        </div>

        <Reveal delay={120}>
          <div className="relative mt-16 overflow-hidden rounded-[2rem] bg-ink px-6 py-9 text-cream sm:px-10 sm:py-12">
            <div className="grain absolute inset-0 opacity-50" aria-hidden="true" />
            <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-[radial-gradient(circle,hsl(var(--lime)/0.16),transparent_62%)] blur-2xl" />
            <div className="relative grid gap-9 lg:grid-cols-12 lg:items-center">
              <div className="lg:col-span-5">
                <div className="eyebrow text-lime/70">API first</div>
                <h3 className="display mt-4 text-[clamp(1.9rem,3.4vw,2.9rem)] leading-[1.06]">
                  自带引擎，
                  <br />
                  也自带接口。
                </h3>
                <p className="mt-4 max-w-md text-[0.875rem] leading-relaxed text-cream/55">
                  FastAPI 提供同步与异步求解端点，OpenAPI 文档开箱即用。用 API Key 或 JWT
                  接入你已有的调度系统。
                </p>
                <div className="mt-6 flex flex-wrap gap-2">
                  {["FastAPI", "OR-Tools", "REST", "API Key / JWT"].map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-cream/15 px-2.5 py-1 font-mono text-[0.5625rem] uppercase tracking-[0.12em] text-cream/55"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              <div className="lg:col-span-7">
                <div className="overflow-hidden rounded-2xl border border-cream/10 bg-ink-soft">
                  <div className="flex items-center justify-between border-b border-cream/10 px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-amber/70" />
                      <span className="h-2 w-2 rounded-full bg-cream/20" />
                      <span className="h-2 w-2 rounded-full bg-lime/60" />
                      <span className="ml-2 font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-cream/35">
                        request.http
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={copy}
                      className="inline-flex items-center gap-1.5 rounded-full border border-cream/15 px-2.5 py-1 text-[0.625rem] text-cream/55 transition-colors hover:border-lime/40 hover:text-lime"
                    >
                      {copied ? <Check className="h-3 w-3 text-lime" /> : <Copy className="h-3 w-3" />}
                      {copied ? "已复制" : "复制"}
                    </button>
                  </div>
                  <pre className="overflow-x-auto px-4 py-5 font-mono text-[0.6875rem] leading-relaxed text-cream/70 sm:px-5">
                    <code>
                      <span className="text-lime">POST</span> /api/v1/solve{"\n"}
                      <span className="text-cream/35">X-API-Key:</span> ••••••••{"\n\n"}
                      {"{\n"}
                      {"  "}
                      <span className="text-mint">"customers"</span>: [ ...13 nodes ],{"\n"}
                      {"  "}
                      <span className="text-mint">"params"</span>: {"{\n"}
                      {"    "}
                      <span className="text-mint">"carbon_price"</span>: 0.08,{"\n"}
                      {"    "}
                      <span className="text-mint">"search_time_limit"</span>: 45{"\n"}
                      {"  }\n"}
                      {"}"}
                    </code>
                  </pre>
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-cream/30">
                  <span>OpenAPI · /docs</span>
                  <span>同步 / 异步 · Webhook 回调</span>
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
