import { useState } from "react"
import { Minus, Plus, Settings2 } from "lucide-react"
import {
  vehicleColor,
  vehicleLabel,
  VEHICLE_SPEC_FIELDS,
  type VehicleSpecField,
} from "@/lib/data"
import type { VehicleSpec, VehicleType } from "@/lib/types"
import { cn } from "@/lib/utils"

interface FleetStepperProps {
  type: VehicleType
  spec: VehicleSpec
  maxCount: number
  canRemove: boolean
  onChange: (count: number) => void
  onSpecChange: (key: VehicleSpecField, value: number) => void
  onRemove: () => void
}

export function FleetStepper({
  type,
  spec,
  maxCount,
  canRemove,
  onChange,
  onSpecChange,
  onRemove,
}: FleetStepperProps) {
  const [open, setOpen] = useState(false)
  const label = vehicleLabel(type, spec)

  return (
    <div className="border-t border-cream/10 py-3 first:border-0 first:pt-0 last:pb-0">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="h-2 w-2 shrink-0 rounded-full"
            style={{ background: vehicleColor(type, spec) }}
            aria-hidden="true"
          />
          <div className="min-w-0">
            <div className="truncate text-[0.8125rem] font-medium text-cream/85">{label}</div>
            <div className="mt-0.5 font-mono text-[0.625rem] text-cream/55">
              {spec.capacity} 件 · ¥{spec.fixed_cost}/车 · {spec.fuel_per_100km} L/100km · {spec.speed_kmh} km/h
            </div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            aria-label={`编辑${label}参数`}
            aria-expanded={open}
            title="编辑载重 / 成本 / 油耗 / 速度"
            onClick={() => setOpen((value) => !value)}
            className={cn(
              "grid h-7 w-7 place-items-center rounded-full border transition-colors",
              open
                ? "border-lime/50 text-lime"
                : "border-cream/15 text-cream/55 hover:border-lime/40 hover:text-lime",
            )}
          >
            <Settings2 className="h-3 w-3" />
          </button>
          <button
            type="button"
            aria-label={`减少${label}数量`}
            disabled={spec.count <= 0}
            onClick={() => onChange(spec.count - 1)}
            className="grid h-7 w-7 place-items-center rounded-full border border-cream/15 text-cream/65 transition-colors hover:border-lime/40 hover:text-lime disabled:cursor-not-allowed disabled:opacity-30"
          >
            <Minus className="h-3 w-3" />
          </button>
          <input
            type="number"
            min={0}
            max={maxCount}
            step={1}
            value={spec.count}
            aria-label={`${label}数量`}
            onFocus={(event) => event.currentTarget.select()}
            onChange={(event) => {
              const next = Number(event.target.value)
              if (Number.isFinite(next)) {
                onChange(Math.max(0, Math.min(maxCount, next)))
              }
            }}
            className={cn(
              "w-9 bg-transparent text-center font-mono text-sm tabular-nums outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none",
              spec.count > 0 ? "text-cream" : "text-amber",
            )}
          />
          <button
            type="button"
            aria-label={`增加${label}数量`}
            disabled={spec.count >= maxCount}
            onClick={() => onChange(spec.count + 1)}
            className="grid h-7 w-7 place-items-center rounded-full border border-cream/15 text-cream/65 transition-colors hover:border-lime/40 hover:text-lime disabled:cursor-not-allowed disabled:opacity-30"
          >
            <Plus className="h-3 w-3" />
          </button>
        </div>
      </div>

      {open && (
        <>
          <div className="mt-2.5 grid grid-cols-2 gap-2">
            {VEHICLE_SPEC_FIELDS.map((field) => (
              <label
                key={field.key}
                className="rounded-lg border border-cream/10 bg-ink/30 px-2.5 py-1.5 transition-colors focus-within:border-lime/40"
              >
                <span className="flex items-baseline justify-between gap-2 text-[0.625rem] text-cream/45">
                  <span>{field.label}</span>
                  <span className="font-mono text-cream/30">{field.suffix}</span>
                </span>
                <input
                  type="number"
                  min={field.min}
                  max={field.max}
                  step={field.step}
                  value={spec[field.key]}
                  aria-label={`${label}${field.label}`}
                  onFocus={(event) => event.currentTarget.select()}
                  onChange={(event) => {
                    const next = Number(event.target.value)
                    if (Number.isFinite(next)) {
                      onSpecChange(field.key, next)
                    }
                  }}
                  className="mt-0.5 w-full bg-transparent font-mono text-[0.8125rem] text-cream outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                />
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={onRemove}
            disabled={!canRemove}
            className="mt-2 text-[0.6875rem] text-amber/75 transition-colors hover:text-amber disabled:cursor-not-allowed disabled:opacity-30"
            title={canRemove ? "删除此车型" : "至少保留一种车型"}
          >
            删除此车型
          </button>
        </>
      )}
    </div>
  )
}