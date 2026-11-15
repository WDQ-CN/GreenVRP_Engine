import { ArrowUp } from "lucide-react"
import { Logo } from "@/components/ui/logo"

const LINKS = [
  { label: "引擎", href: "#engine" },
  { label: "优化控制台", href: "#console" },
  { label: "方案结果", href: "#results" },
  { label: "能力矩阵", href: "#capabilities" },
]

export function Footer() {
  return (
    <footer className="border-t border-cream/10 bg-ink pb-8 pt-14 text-cream">
      <div className="container-x">
        <div className="grid gap-10 md:grid-cols-12">
          <div className="md:col-span-5">
            <Logo tone="light" />
            <p className="mt-4 max-w-xs text-[0.8125rem] leading-relaxed text-cream/60">
              碳感知的车辆路径优化引擎。让成本、时间与碳排，在同一个目标函数里被认真权衡。
            </p>
            <p className="mt-5 font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-cream/25">
              Built with OR-Tools · FastAPI · React
            </p>
          </div>

          <div className="md:col-span-3">
            <div className="eyebrow text-cream/55">Navigate</div>
            <ul className="mt-4 space-y-2.5">
              {LINKS.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className="link-underline text-[0.8125rem] text-cream/55 transition-colors hover:text-cream"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div className="md:col-span-4">
            <div className="eyebrow text-cream/55">Data note</div>
            <p className="mt-4 text-[0.75rem] leading-relaxed text-cream/55">
              页面默认运行本地演示解算，使用内置北京样例数据。连接 FastAPI
              后端后，可切换为真实的 OR-Tools 求解结果。
            </p>
            <a
              href="#top"
              className="mt-5 inline-flex items-center gap-1.5 rounded-full border border-cream/15 px-3 py-1.5 text-[0.6875rem] text-cream/55 transition-colors hover:border-lime/40 hover:text-lime"
            >
              回到顶部
              <ArrowUp className="h-3 w-3" />
            </a>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-cream/10 pt-6 text-[0.625rem] text-cream/45 sm:flex-row sm:items-center">
          <span>© 2026 GreenVRP Engine · 为更轻的物流而构建</span>
          <span className="font-mono uppercase tracking-[0.16em]">Less carbon, same promise.</span>
        </div>
      </div>
    </footer>
  )
}
