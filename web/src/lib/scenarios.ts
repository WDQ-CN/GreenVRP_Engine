import { api } from './api';
import type {
  BackendSolverParams,
  BackendVehicleConfigItem,
  Customer,
  Scenario,
  VehicleSpec,
} from '@/types';

export interface ScenarioCreateRequest {
  name: string;
  description?: string;
  customers: Customer[];
  vehicle_config?: Record<string, BackendVehicleConfigItem>;
  params?: BackendSolverParams;
}

export interface ScenarioListItem {
  id: number;
  name: string;
  description?: string;
  customer_count: number;
  solution_count: number;
  created_at: string;
  updated_at?: string;
}

export interface ScenarioDetailData {
  id: number;
  name: string;
  description?: string;
  customers: Customer[];
  vehicle_config?: Record<string, BackendVehicleConfigItem>;
  params?: BackendSolverParams;
  created_at: string;
  updated_at?: string;
}

export function vehicleConfigMapToArray(
  map: Record<string, BackendVehicleConfigItem>
): VehicleSpec[] {
  return Object.entries(map).map(([type, config]) => ({
    type,
    count: config.count,
    capacity: config.capacity,
    fixed_cost: config.fixed_cost,
    fuel_consumption_per_100km: config.fuel_per_100km,
    avg_speed_kmh: config.speed_kmh,
    color: config.color,
    emission_kg_per_km: 0.3,
  }));
}

export async function listScenarios(): Promise<ScenarioListItem[]> {
  const { data } = await api.get<ScenarioListItem[]>('/scenarios');
  return data;
}

export async function createScenario(
  request: ScenarioCreateRequest
): Promise<ScenarioListItem> {
  const { data } = await api.post<ScenarioListItem>('/scenarios', request);
  return data;
}

export async function getScenario(id: number): Promise<ScenarioDetailData> {
  const { data } = await api.get<ScenarioDetailData>(`/scenarios/${id}`);
  return data;
}

export async function updateScenario(
  id: number,
  request: Partial<ScenarioCreateRequest>
): Promise<ScenarioListItem> {
  const { data } = await api.put<ScenarioListItem>(`/scenarios/${id}`, request);
  return data;
}

export async function deleteScenario(id: number): Promise<void> {
  await api.delete(`/scenarios/${id}`);
}

export function scenarioToSolveRequest(
  scenario: Scenario
): ScenarioCreateRequest {
  return {
    name: scenario.name,
    description: scenario.description,
    customers: scenario.data.customers,
    vehicle_config: scenario.data.vehicle_config,
    params: scenario.data.params,
  };
}
