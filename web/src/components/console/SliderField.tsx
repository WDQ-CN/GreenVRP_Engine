import type { CSSProperties } from "react"
import { formatNumber } from "@/lib/format"

interface SliderFieldProps {
  label: string
  value: number
  min: number
  max: number
  step: number
  prefix?: string
  suffix?: string
  decimals?: number
  onChange: (value: number) => void
}

export function SliderField({
  label,
  value,
  min,
  max,
  step,
  prefix = "",
  suffix = "",
  decimals = 2,
  onChange,
}: SliderFieldProps) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <label className="block">
      <span className="flex items-baseline justify-between gap-3">
        <span className="text-[0.75rem] text-cream/55">{label}</span>
        <span className="font-mono text-[0.75rem] text-lime">
          {prefix}
          {formatNumber(value, decimals)}
          {suffix && <span className="ml-1 text-cream/50">{suffix}</span>}
        </span>
      </span>
      <input
        type="range"
        className="range-input mt-1"
        style={{ "--fill": `${pct}%` } as CSSProperties}
        min={min}
        max={max}
        step={step}
        value={value}
        aria-label={label}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  )
}
