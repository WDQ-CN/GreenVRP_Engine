export type VehicleType = string

export interface VehicleSpec {
  capacity: number
  fixed_cost: number
  fuel_per_100km: number
  speed_kmh: number
  count: number
  label?: string
  color?: string
}

export type VehicleConfigMap = Record<VehicleType, VehicleSpec>

export interface Customer {
  id: number
  name: string
  lat: number
  lon: number
  demand: number
  service_time_min: number
  tw_earliest: number
  tw_latest: number
}

export interface Stop {
  node: number
  customer_id: number | null
  customer_name: string
  lat: number
  lon: number
  demand: number
  service_time: number
  arrival_time?: number
  departure_time?: number
  tw_earliest?: number
  tw_latest?: number
  late_minutes?: number
  is_late?: boolean
}

export interface RoutePlan {
  vehicle_id: number
  vehicle_type: VehicleType
  vehicle_color: string
  capacity: number
  stops: Stop[]
  distance_km: number
  total_demand: number
  total_time_min: number
  late_minutes: number
}

export interface SolveSolution {
  routes: RoutePlan[]
  total_distance: number
  vehicles_used: Partial<Record<VehicleType, number>>
  total_late_minutes: number
  solution_status: string
  solve_time_seconds: number
}

export interface CostResult {
  transport_cost: number
  labor_cost: number
  fixed_cost: number
  penalty_cost: number
  carbon_cost: number
  total_cost: number
  carbon_emission_kg: number
  total_distance_km: number
  total_time_min: number
  driving_time_min: number
  service_time_min: number
  waiting_time_min: number
  cost_breakdown: Record<string, number>
}

export interface SolverSettings {
  fuel_price: number
  hourly_wage: number
  carbon_price: number
  late_penalty_per_min: number
  search_time_limit: number
  use_multi_strategy: boolean
  use_parallel: boolean
}

export type SolverPreset = "balanced" | "carbon" | "speed"

export interface Baseline {
  distance_km: number
  carbon_kg: number
}

export interface SolveOutcome {
  solution: SolveSolution
  cost: CostResult
  customers: Customer[]
  baseline: Baseline
  source: "demo" | "api"
  solvedAt: string
  note?: string
}

export interface ApiConnection {
  apiBase: string
  apiKey: string
  mode: "demo" | "api"
}
