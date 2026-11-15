import { useEffect, useState } from "react"
import { Check, Loader2, X, Zap } from "lucide-react"
import { buttonVariants } from "@/components/ui/button"
import { useSolver } from "@/state/SolverProvider"
import { DEMO_API_BASE, DEMO_API_KEY } from "@/lib/data"
import { cn } from "@/lib/utils"

type TestState = { state: "idle" | "testing" | "ok" | "error"; message: string }

export function ConnectDialog() {
  const { connectOpen, closeConnect, connection, saveConnection, testCurrentConnection } = useSolver()
  const [apiBase, setApiBase] = useState(connection.apiBase)
  const [apiKey, setApiKey] = useState(connection.apiKey)
  const [test, setTest] = useState<TestState>({ state: "idle", message: "" })

  useEffect(() => {
    if (connectOpen) {
      setApiBase(connection.apiBase)
      setApiKey(connection.apiKey)
      setTest({ state: "idle", message: "" })
    }
  }, [connectOpen, connection])

  useEffect(() => {
    if (!connectOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeConnect()
    }
    document.addEventListener("keydown", onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", onKey)
      document.body.style.overflow = previous
    }
  }, [connectOpen, closeConnect])

  if (!connectOpen) return null

  const runTest = async () => {
    setTest({ state: "testing", message: "正在握手…" })
    const result = await testCurrentConnection({ apiBase, apiKey, mode: "api" })
    setTest({ state: result.ok ? "ok" : "error", message: result.message })
  }

  const enable = () => {
    saveConnection({ apiBase, apiKey, mode: "api" })
    closeConnect()
  }

  const useFreshDemo = () => {
    saveConnection({ apiBase: DEMO_API_BASE, apiKey: DEMO_API_KEY, mode: "demo" })
    closeConnect()
  }

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center p-4"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) closeConnect()
      }}
    >
      <div className="absolute inset-0 bg-ink/75 backdrop-blur-sm" aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="connect-title"
        className="animate-rise relative w-full max-w-lg overflow-hidden rounded-[1.75rem] border border-ink/10 bg-paper p-6 text-ink shadow-lift sm:p-8"
      >
        <div className="grain pointer-events-none absolute inset-0 opacity-40" aria-hidden="true" />
        <div className="relative">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="eyebrow text-forest/55">Engine connection</div>
              <h2 id="connect-title" className="mt-2 font-serif text-[1.8rem] leading-tight">
                连接真实引擎
              </h2>
            </div>
            <button
              type="button"
              onClick={closeConnect}
              aria-label="关闭连接设置"
              className="grid h-8 w-8 place-items-center rounded-full border border-ink/10 text-ink/45 transition-colors hover:border-ink/25 hover:text-ink"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          <p className="mt-3 text-[0.8125rem] leading-relaxed text-ink/65">
            FastAPI 默认监听 <span className="font-mono text-[0.75rem]">localhost:8000</span>。
            启动后端后，可将解算切换到 OR-Tools 多策略求解。
          </p>

          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="text-[0.75rem] font-medium text-ink/65">API 地址</span>
              <input
                type="url"
                value={apiBase}
                autoFocus
                spellCheck={false}
                onChange={(event) => setApiBase(event.target.value)}
                placeholder="http://localhost:8000"
                className="mt-1.5 h-11 w-full rounded-xl border border-ink/15 bg-cream px-3.5 font-mono text-[0.75rem] text-ink outline-none transition-colors placeholder:text-ink/25 focus:border-forest/50"
              />
            </label>
            <label className="block">
              <span className="flex items-center justify-between text-[0.75rem] font-medium text-ink/65">
                API Key
                <button
                  type="button"
                  onClick={() => {
                    setApiBase(DEMO_API_BASE)
                    setApiKey(DEMO_API_KEY)
                    setTest({ state: "idle", message: "" })
                  }}
                  className="font-normal text-forest/60 underline decoration-forest/25 underline-offset-2 hover:text-forest"
                >
                  填入本地开发默认值
                </button>
              </span>
              <input
                type="password"
                value={apiKey}
                autoComplete="off"
                spellCheck={false}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="X-API-Key"
                className="mt-1.5 h-11 w-full rounded-xl border border-ink/15 bg-cream px-3.5 font-mono text-[0.75rem] text-ink outline-none transition-colors placeholder:text-ink/25 focus:border-forest/50"
              />
            </label>
          </div>

          <div className="mt-4 flex items-center gap-2 text-[0.6875rem]">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                test.state === "ok" && "bg-forest",
                test.state === "error" && "bg-destructive",
                (test.state === "idle" || test.state === "testing") && "bg-ink/25",
              )}
            />
            <span
              className={cn(
                test.state === "error" ? "text-destructive" : "text-ink/65",
                test.state === "ok" && "text-forest",
              )}
              aria-live="polite"
            >
              {test.state === "testing" ? "正在测试连接…" : test.message || "尚未测试连接"}
            </span>
          </div>

          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={runTest}
              disabled={test.state === "testing" || !apiBase || !apiKey}
              className={cn(buttonVariants({ variant: "outline", size: "md" }), "flex-1")}
            >
              {test.state === "testing" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : test.state === "ok" ? (
                <Check className="h-4 w-4 text-forest" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              测试连接
            </button>
            <button
              type="button"
              onClick={enable}
              disabled={!apiBase || !apiKey}
              className={cn(buttonVariants({ variant: "lime", size: "md" }), "flex-1")}
            >
              保存并启用
            </button>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-ink/10 pt-4">
            <button
              type="button"
              onClick={useFreshDemo}
              className="text-[0.6875rem] text-ink/60 underline decoration-ink/20 underline-offset-2 transition-colors hover:text-ink"
            >
              切回本地演示解算
            </button>
            <span className="font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-ink/45">
              {connection.mode === "api" ? "当前：真实引擎" : "当前：演示模式"}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
