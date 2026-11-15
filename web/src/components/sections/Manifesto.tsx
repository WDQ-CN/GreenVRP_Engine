import { ArrowUpRight } from "lucide-react"
import { Reveal } from "@/components/ui/reveal"
import { SectionHeading } from "@/components/ui/section-heading"
import { LedgerVisual } from "@/components/visuals/LedgerVisual"

const PRINCIPLES = [
  {
    index: "01",
    title: "目标函数里，有碳的重量",
    body: "柴油每升 2.63 kg CO₂ 直接进入成本模型。减排不是事后报表，而是求解时就被最小化的变量。",
  },
  {
    index: "02",
    title: "约束真实，方案才可执行",
    body: "软时间窗允许迟到，同时用罚金量化代价；容量与服务时长始终是硬边界。",
  },
  {
    index: "03",
    title: "车型不是标签，是变量",
    body: "4.2m / 7.6m / 9.6m 的载重、油耗与速度一起参与决策，让车队结构匹配真实需求。",
  },
]

export function Manifesto() {
  return (
    <section id="engine" className="relative overflow-hidden bg-paper py-24 sm:py-32">
      <div className="pointer-events-none absolute -left-40 top-24 h-[28rem] w-[28rem] rounded-full border border-ink/5" />
      <div className="container-x relative">
        <div className="grid gap-14 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-5">
            <Reveal>
              <SectionHeading
                index="01"
                eyebrow="Why GreenVRP"
                title={
                  <>
                    路线优化，
                    <br />
                    不该只算运费。
                  </>
                }
                lead="碳排放不是报表里的脚注，而是成本函数中的一项。GreenVRP 让每一次调度都同时回答：花多少、快多少、排多少。"
              />
            </Reveal>

            <div className="mt-10 space-y-7">
              {PRINCIPLES.map((item, index) => (
                <Reveal key={item.index} delay={100 + index * 90}>
                  <div className="group grid grid-cols-[2.25rem_1fr] gap-4 border-t border-ink/10 pt-5">
                    <span className="font-mono text-[0.625rem] uppercase tracking-[0.2em] text-forest/75">
                      {item.index}
                    </span>
                    <div>
                      <h3 className="font-serif text-[1.35rem] leading-tight text-ink">{item.title}</h3>
                      <p className="mt-2 text-[0.8125rem] leading-relaxed text-ink/70">{item.body}</p>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>

            <Reveal delay={360}>
              <a
                href="#capabilities"
                className="link-underline mt-9 inline-flex items-center gap-2 text-[0.8125rem] font-medium text-ink"
              >
                查看完整能力矩阵
                <ArrowUpRight className="h-4 w-4" />
              </a>
            </Reveal>
          </div>

          <Reveal delay={160} className="lg:col-span-7">
            <LedgerVisual />
          </Reveal>
        </div>

        <Reveal delay={120}>
          <figure className="mt-24 grid gap-8 border-t border-ink/10 pt-12 lg:grid-cols-12">
            <span className="eyebrow text-forest/55 lg:col-span-2">Design principle</span>
            <blockquote className="display text-[clamp(1.9rem,3.8vw,3.25rem)] leading-[1.08] text-ink lg:col-span-9">
              “最短的路线，不一定是更轻的路线。
              <span className="text-forest/70">真正好的方案，在成本、时间与碳之间找到可执行的平衡。”</span>
            </blockquote>
          </figure>
        </Reveal>
      </div>
    </section>
  )
}
