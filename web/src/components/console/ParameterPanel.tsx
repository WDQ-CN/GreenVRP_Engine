import { useState, type FormEvent } from "react"
import { MAX_FLEET_SIZE, PRESETS } from "@/lib/data"
import type { SolverPreset } from "@/lib/types"
import { cn } from "@/lib/utils"
import { useSolver } from "@/state/SolverProvider"
import { SliderField } from "./SliderField"
import { FleetStepper } from "./FleetStepper"

const STRATEGIES = [
  { label: "快速", seconds: 20, hint: "20s" },
  { label: "均衡", seconds: 45, hint: "45s" },
  { label: "深度", seconds: 90, hint: "90s" },
]

export function ParameterPanel() {
  const {
    settings,
    vehicles,
    preset,
    applyPreset,
    updateSetting,
    updateVehicleCount,
    updateVehicleSpec,
    addVehicleType,
    removeVehicleType,
  } = useSolver()
  const [newVehicleName, setNewVehicleName] = useState("")
  const [addVehicleError, setAddVehicleError] = useState<string | null>(null)

  const vehicleOrder = Object.keys(vehicles)
  const fleetTotal = vehicleOrder.reduce((sum, type) => sum + vehicles[type].count, 0)
  const handleAddVehicle = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const error = addVehicleType(newVehicleName)
    if (error) {
      setAddVehicleError(error)
      return
    }
    setNewVehicleName("")
    setAddVehicleError(null)
  }
  const presets = Object.keys(PRESETS) as SolverPreset[]

  return (
    <div className="space-y-7">
      <div>
        <div className="mb-3 flex items-center justify-between">
          <span className="eyebrow text-cream/55">Scenario preset</span>
          <span className="font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-cream/30">
            参数仅影响下一次解算
          </span>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="方案预设">
          {presets.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => applyPreset(key)}
              title={PRESETS[key].hint}
              className={cn(
                "rounded-full border px-3.5 py-1.5 text-[0.75rem] font-medium transition-all duration-300",
                preset === key
                  ? "border-lime bg-lime text-ink"
                  : "border-cream/15 text-cream/55 hover:border-cream/30 hover:text-cream",
              )}
            >
              {PRESETS[key].label}
            </button>
          ))}
        </div>
      </div>

      <div className="hairline-dark" />

      <div>
        <div className="mb-4 flex items-center justify-between">
          <span className="eyebrow text-cream/55">经济参数</span>
          <span className="font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-cream/30">
            五维成本输入
          </span>
        </div>
        <div className="grid gap-x-7 gap-y-5 sm:grid-cols-2">
          <SliderField
            label="碳价"
            value={settings.carbon_price}
            min={0}
            max={0.3}
            step={0.01}
            prefix="¥"
            suffix="/kg"
            onChange={(value) => updateSetting("carbon_price", value)}
          />
          <SliderField
            label="柴油价格"
            value={settings.fuel_price}
            min={5}
            max={10}
            step={0.1}
            prefix="¥"
            suffix="/L"
            decimals={1}
            onChange={(value) => updateSetting("fuel_price", value)}
          />
          <SliderField
            label="人工时薪"
            value={settings.hourly_wage}
            min={30}
            max={80}
            step={5}
            prefix="¥"
            suffix="/h"
            decimals={0}
            onChange={(value) => updateSetting("hourly_wage", value)}
          />
          <SliderField
            label="迟到罚金"
            value={settings.late_penalty_per_min}
            min={0}
            max={30}
            step={1}
            prefix="¥"
            suffix="/min"
            decimals={0}
            onChange={(value) => updateSetting("late_penalty_per_min", value)}
          />
        </div>
      </div>

      <div className="hairline-dark" />

      <div>
        <div className="mb-3 flex items-center justify-between">
          <span className="eyebrow text-cream/55">车队编成</span>
          <span className="font-mono text-[0.625rem] text-cream/55">
            共 {fleetTotal} / {MAX_FLEET_SIZE} 辆可用
          </span>
        </div>
        <div>
          {vehicleOrder.map((type) => (
            <FleetStepper
              key={type}
              type={type}
              spec={vehicles[type]}
              maxCount={Math.min(
                MAX_FLEET_SIZE,
                vehicles[type].count + (MAX_FLEET_SIZE - fleetTotal),
              )}
              canRemove={vehicleOrder.length > 1}
              onChange={(count) => updateVehicleCount(type, count)}
              onSpecChange={(key, value) => updateVehicleSpec(type, key, value)}
              onRemove={() => {
                setAddVehicleError(null)
                removeVehicleType(type)
              }}
            />
          ))}
        </div>
        <form onSubmit={handleAddVehicle} className="mt-3 flex items-center gap-2">
          <input
            value={newVehicleName}
            onChange={(event) => {
              setNewVehicleName(event.target.value)
              setAddVehicleError(null)
            }}
            placeholder="新增车型，如 6.8m"
            maxLength={20}
            aria-label="新增车型名称"
            className="min-w-0 flex-1 rounded-lg border border-cream/10 bg-ink/30 px-2.5 py-1.5 text-[0.75rem] text-cream outline-none transition-colors placeholder:text-cream/30 focus:border-lime/40"
          />
          <button
            type="submit"
            className="shrink-0 rounded-lg border border-lime/40 px-3 py-1.5 text-[0.75rem] font-medium text-lime transition-colors hover:bg-lime/10"
          >
            新增车型
          </button>
        </form>
        {addVehicleError && (
          <p className="mt-1.5 text-[0.6875rem] text-amber" role="alert">
            {addVehicleError}
          </p>
        )}
        <p className="mt-3 text-[0.6875rem] leading-relaxed text-cream/40">
          数量可直接输入；点击齿轮可编辑载重、发车成本、百公里油耗与平均速度，也可删除自定义车型。
        </p>
        {fleetTotal === 0 && (
          <p className="mt-3 text-[0.75rem] text-amber" role="alert">
            至少启用一种车型，否则无法构造路线。
          </p>
        )}
      </div>

      <div className="hairline-dark" />

      <div>
        <div className="mb-3 flex items-center justify-between">
          <span className="eyebrow text-cream/55">求解预算</span>
          <span className="font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-cream/30">
            时间上限
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2" role="group" aria-label="求解时间预算">
          {STRATEGIES.map((strategy) => (
            <button
              key={strategy.seconds}
              type="button"
              onClick={() => updateSetting("search_time_limit", strategy.seconds)}
              className={cn(
                "flex flex-col items-start rounded-xl border px-3.5 py-2.5 text-left transition-all duration-300",
                settings.search_time_limit === strategy.seconds
                  ? "border-lime/60 bg-lime/10"
                  : "border-cream/10 hover:border-cream/25",
              )}
            >
              <span className="text-[0.8125rem] font-medium text-cream/85">{strategy.label}</span>
              <span className="mt-1 font-mono text-[0.625rem] text-cream/50">{strategy.hint}</span>
            </button>
          ))}
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={settings.use_multi_strategy}
          onClick={() => updateSetting("use_multi_strategy", !settings.use_multi_strategy)}
          className="mt-4 flex w-full items-center justify-between gap-4 rounded-xl border border-cream/10 px-3.5 py-3 text-left transition-colors hover:border-cream/20"
        >
          <span>
            <span className="block text-[0.8125rem] font-medium text-cream/85">多策略并行</span>
            <span className="mt-0.5 block text-[0.6875rem] text-cream/55">
              5 组首解策略 × 局部搜索，择优返回
            </span>
          </span>
          <span
            className={cn(
              "relative h-5 w-9 shrink-0 rounded-full p-0.5 transition-colors duration-300",
              settings.use_multi_strategy ? "bg-lime" : "bg-cream/20",
            )}
          >
            <span
              className={cn(
                "block h-4 w-4 rounded-full bg-ink transition-transform duration-300",
                settings.use_multi_strategy && "translate-x-4",
              )}
            />
          </span>
        </button>
      </div>
    </div>
  )
}
