import { useEffect, useState } from "react"
import { SolverProvider } from "@/state/SolverProvider"
import { Navbar } from "@/components/layout/Navbar"
import { Footer } from "@/components/layout/Footer"
import { ConnectDialog } from "@/components/layout/ConnectDialog"
import { Hero } from "@/components/sections/Hero"
import { Ticker } from "@/components/sections/Ticker"
import { Manifesto } from "@/components/sections/Manifesto"
import { Console } from "@/components/sections/Console"
import { Results } from "@/components/sections/Results"
import { Capabilities } from "@/components/sections/Capabilities"
import { ClosingCta } from "@/components/sections/ClosingCta"

function ScrollProgress() {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const update = () => {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight
      setProgress(scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0)
    }
    update()
    window.addEventListener("scroll", update, { passive: true })
    window.addEventListener("resize", update)
    return () => {
      window.removeEventListener("scroll", update)
      window.removeEventListener("resize", update)
    }
  }, [])

  return (
    <div className="fixed inset-x-0 top-0 z-[60] h-[2px] bg-transparent" aria-hidden="true">
      <div
        className="h-full bg-gradient-to-r from-lime via-mint to-lime transition-[width] duration-150 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  )
}

export default function App() {
  useEffect(() => {
    const hash = window.location.hash.slice(1)
    if (!hash) return
    const timer = window.setTimeout(() => {
      document.getElementById(decodeURIComponent(hash))?.scrollIntoView({ behavior: "auto", block: "start" })
    }, 140)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <SolverProvider>
      <a
        href="#console"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-full focus:bg-lime focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-ink"
      >
        跳到优化控制台
      </a>
      <ScrollProgress />
      <Navbar />
      <main>
        <Hero />
        <Ticker />
        <Manifesto />
        <Console />
        <Results />
        <Capabilities />
        <ClosingCta />
      </main>
      <Footer />
      <ConnectDialog />
    </SolverProvider>
  )
}
