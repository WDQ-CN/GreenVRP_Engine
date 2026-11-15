import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import { DEMO_API_BASE, DEMO_API_KEY, DEFAULT_SETTINGS, DEFAULT_VEHICLES, DEMO_CUSTOMERS, MAX_FLEET_SIZE, PRESETS, ROUTE_PALETTE, VEHICLE_SPEC_FIELDS, type VehicleSpecField } from "@/lib/data"
import { solveDemo } from "@/lib/demoSolver"
import { solveViaApi, testConnection } from "@/lib/apiSolver"
import type {
  ApiConnection,
  SolverPreset,
  SolverSettings,
  SolveOutcome,
  VehicleConfigMap,
  VehicleType,
} from "@/lib/types"

const CONNECTION_KEY = "greenvrp.connection.v1"

function loadConnection(): ApiConnection {
  try {
    const raw = window.localStorage.getItem(CONNECTION_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<ApiConnection>
      return {
        apiBase: parsed.apiBase || DEMO_API_BASE,
        apiKey: parsed.apiKey || DEMO_API_KEY,
        mode: parsed.mode === "api" ? "api" : "demo",
      }
    }
  } catch {
    /* ignore corrupted storage */
  }
  return { apiBase: DEMO_API_BASE, apiKey: DEMO_API_KEY, mode: "demo" }
}

interface SolverContextValue {
  settings: SolverSettings
  vehicles: VehicleConfigMap
  outcome: SolveOutcome
  status: "idle" | "running" | "success" | "error"
  error: string | null
  preset: SolverPreset | null
  connection: ApiConnection
  connectOpen: boolean
  updateSetting: (key: keyof SolverSettings, value: number | boolean) => void
  updateVehicleCount: (type: VehicleType, count: number) => void
  updateVehicleSpec: (type: VehicleType, key: VehicleSpecField, value: number) => void
  addVehicleType: (name: string) => string | null
  removeVehicleType: (type: VehicleType) => void
  applyPreset: (preset: SolverPreset) => void
  runSolve: () => Promise<boolean>
  openConnect: () => void
  closeConnect: () => void
  saveConnection: (next: ApiConnection) => void
  testCurrentConnection: (next: ApiConnection) => Promise<{ ok: boolean; message: string }>
}

const SolverContext = createContext<SolverContextValue | null>(null)

export function SolverProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<SolverSettings>(DEFAULT_SETTINGS)
  const [vehicles, setVehicles] = useState<VehicleConfigMap>(DEFAULT_VEHICLES)
  const [preset, setPreset] = useState<SolverPreset | null>("balanced")
  const [outcome, setOutcome] = useState<SolveOutcome>(() =>
    solveDemo(DEMO_CUSTOMERS, DEFAULT_VEHICLES, DEFAULT_SETTINGS),
  )
  const [status, setStatus] = useState<"idle" | "running" | "success" | "error">("idle")
  const [error, setError] = useState<string | null>(null)
  const [connection, setConnection] = useState<ApiConnection>(loadConnection)
  const [connectOpen, setConnectOpen] = useState(false)

  const updateSetting = useCallback((key: keyof SolverSettings, value: number | boolean) => {
    setSettings((current) => ({ ...current, [key]: value }))
    setPreset(null)
  }, [])

  const updateVehicleCount = useCallback((type: VehicleType, count: number) => {
    setVehicles((current) => ({
      ...current,
      [type]: {
        ...current[type],
        count: Math.max(0, Math.min(MAX_FLEET_SIZE, Math.round(count))),
      },
    }))
    setPreset(null)
  }, [])

  const updateVehicleSpec = useCallback(
    (type: VehicleType, key: VehicleSpecField, value: number) => {
      const field = VEHICLE_SPEC_FIELDS.find((item) => item.key === key)
      const bounded = field
        ? Math.min(field.max, Math.max(field.min, value))
        : value
      setVehicles((current) => ({
        ...current,
        [type]: {
          ...current[type],
          [key]: key === "capacity" ? Math.round(bounded) : bounded,
        },
      }))
      setPreset(null)
    },
    [],
  )

  const addVehicleType = useCallback(
    (rawName: string): string | null => {
      const name = rawName.trim()
      if (!name) return "请输入车型名称"
      if (name.length > 20) return "车型名称不超过 20 个字符"
      if (Object.prototype.hasOwnProperty.call(vehicles, name)) {
        return "该车型已存在"
      }
      const total = Object.values(vehicles).reduce(
        (sum, spec) => sum + spec.count,
        0,
      )
      const usedColors = new Set(
        Object.values(vehicles)
          .map((spec) => spec.color)
          .filter((color): color is string => Boolean(color)),
      )
      const color =
        ROUTE_PALETTE.find((candidate) => !usedColors.has(candidate)) ||
        ROUTE_PALETTE[Object.keys(vehicles).length % ROUTE_PALETTE.length]
      setVehicles((current) => ({
        ...current,
        [name]: {
          label: name,
          color,
          capacity: 1000,
          fixed_cost: 300,
          fuel_per_100km: 15,
          speed_kmh: 35,
          count: total < MAX_FLEET_SIZE ? 1 : 0,
        },
      }))
      setPreset(null)
      return null
    },
    [vehicles],
  )

  const removeVehicleType = useCallback((type: VehicleType) => {
    setVehicles((current) => {
      if (!Object.prototype.hasOwnProperty.call(current, type)) return current
      if (Object.keys(current).length <= 1) return current
      const next = { ...current }
      delete next[type]
      return next
    })
    setPreset(null)
  }, [])

  const applyPreset = useCallback((next: SolverPreset) => {
    setPreset(next)
    setSettings((current) => ({ ...current, ...PRESETS[next].settings }))
  }, [])

  const saveConnection = useCallback((next: ApiConnection) => {
    const normalized: ApiConnection = {
      apiBase: next.apiBase.trim(),
      apiKey: next.apiKey.trim(),
      mode: next.mode,
    }
    setConnection(normalized)
    try {
      window.localStorage.setItem(CONNECTION_KEY, JSON.stringify(normalized))
    } catch {
      /* storage may be blocked */
    }
  }, [])

  const testCurrentConnection = useCallback(
    (next: ApiConnection) => testConnection(next),
    [],
  )

  const runSolve = useCallback(async (): Promise<boolean> => {
    if (status === "running") return false
    setStatus("running")
    setError(null)
    try {
      if (connection.mode === "api") {
        const next = await solveViaApi(DEMO_CUSTOMERS, vehicles, settings, connection)
        setOutcome(next)
      } else {
        await new Promise((resolve) => window.setTimeout(resolve, 950))
        setOutcome(solveDemo(DEMO_CUSTOMERS, vehicles, settings))
      }
      setStatus("success")
      return true
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "求解失败，请重试。")
      setStatus("error")
      return false
    }
  }, [connection, settings, status, vehicles])

  const value = useMemo<SolverContextValue>(
    () => ({
      settings,
      vehicles,
      outcome,
      status,
      error,
      preset,
      connection,
      connectOpen,
      updateSetting,
      updateVehicleCount,
      updateVehicleSpec,
      addVehicleType,
      removeVehicleType,
      applyPreset,
      runSolve,
      openConnect: () => setConnectOpen(true),
      closeConnect: () => setConnectOpen(false),
      saveConnection,
      testCurrentConnection,
    }),
    [
      applyPreset,
      connectOpen,
      connection,
      error,
      outcome,
      preset,
      runSolve,
      saveConnection,
      settings,
      status,
      testCurrentConnection,
      updateSetting,
      updateVehicleCount,
      updateVehicleSpec,
      addVehicleType,
      removeVehicleType,
      vehicles,
    ],
  )

  return <SolverContext.Provider value={value}>{children}</SolverContext.Provider>
}

export function useSolver(): SolverContextValue {
  const context = useContext(SolverContext)
  if (!context) throw new Error("useSolver must be used within SolverProvider")
  return context
}
