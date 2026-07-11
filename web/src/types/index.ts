export interface Customer {
  id: number;
  name: string;
  lat: number;
  lon: number;
  demand: number;
  service_time_min: number;
  tw_earliest: number;
  tw_latest: number;
  is_depot?: boolean;
}

export interface VehicleSpec {
  type: string;
  count: number;
  capacity: number;
  fixed_cost: number;
  fuel_consumption_per_100km: number;
  avg_speed_kmh: number;
  color: string;
  emission_kg_per_km: number;
}

export interface SolverParams {
  fuel_price: number;
  hourly_wage: number;
  carbon_price: number;
  late_penalty_per_min: number;
  search_time_limit: number;
  use_multi_strategy: boolean;
  use_parallel: boolean;
  strategy_weights?: {
    min_distance: number;
    min_vehicles: number;
    min_cost: number;
    min_emission: number;
  };
}

export interface BackendVehicleConfigItem {
  capacity: number;
  fixed_cost: number;
  fuel_per_100km: number;
  speed_kmh: number;
  count: number;
  color: string;
}

export interface BackendSolverParams {
  fuel_price: number;
  hourly_wage: number;
  carbon_price: number;
  late_penalty_per_min: number;
  search_time_limit: number;
  use_multi_strategy: boolean;
  use_parallel: boolean;
}

export interface SolveRequest {
  customers: Customer[];
  vehicle_config?: Record<string, BackendVehicleConfigItem>;
  params?: BackendSolverParams;
  callback_url?: string;
}

export interface RouteStop {
  node: number;
  customer_id: number;
  customer_name: string;
  lat: number;
  lon: number;
  demand: number;
  arrival_time: number | null;
  departure_time?: number | null;
  service_time: number;
  tw_earliest: number;
  tw_latest: number;
  late_minutes: number;
  is_late: boolean;
}

export interface Route {
  vehicle_id: number;
  vehicle_type: string;
  vehicle_color: string;
  capacity: number;
  stops: RouteStop[];
  distance_km: number;
  total_demand: number;
  total_time_min: number;
  late_minutes: number;
}

export interface Solution {
  routes: Route[];
  total_distance: number;
  vehicles_used: Record<string, number>;
  total_late_minutes: number;
  solution_status: string;
  solve_time_seconds: number;
}

export interface CostResult {
  transport_cost: number;
  labor_cost: number;
  fixed_cost: number;
  penalty_cost: number;
  carbon_cost: number;
  total_cost: number;
  carbon_emission_kg: number;
  total_distance_km: number;
  total_time_min: number;
  driving_time_min: number;
  service_time_min: number;
  waiting_time_min: number;
  cost_breakdown: Record<string, number>;
}

export interface SolveResponse {
  job_id: string;
  status: 'completed' | 'pending' | 'processing' | 'failed';
  solution?: Solution;
  cost_result?: CostResult;
  error_message?: string;
  error?: string;
  progress?: number;
  created_at?: string;
  completed_at?: string | null;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  result?: SolveResponse;
  error?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Scenario {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  data: SolveRequest;
}
