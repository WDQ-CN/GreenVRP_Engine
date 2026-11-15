const cny = new Intl.NumberFormat("zh-CN", {
  maximumFractionDigits: 0,
})

const decimal = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

export function formatCNY(value: number): string {
  return `¥${cny.format(Math.round(value))}`
}

export function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

export function formatKm(value: number): string {
  return `${decimal.format(value)} km`
}

export function formatKg(value: number): string {
  return `${decimal.format(value)} kg`
}

export function formatPct(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`
}

export function formatClock(minutes: number): string {
  const total = Math.round(minutes)
  const h = Math.floor(total / 60) % 24
  const m = total % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

export function savingsPct(current: number, baseline: number): number {
  if (baseline <= 0) return 0
  return Math.max(0, ((baseline - current) / baseline) * 100)
}
