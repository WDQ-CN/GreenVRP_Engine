import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type {
  Customer,
  SolverParams,
  SolveResponse,
  VehicleSpec,
} from '@/types';

const DEFAULT_VEHICLE_CONFIG: VehicleSpec[] = [
  {
    type: '4.2m',
    count: 5,
    capacity: 800,
    fixed_cost: 300,
    fuel_consumption_per_100km: 12,
    avg_speed_kmh: 40,
    color: '#2563EB',
    emission_kg_per_km: 0.27,
  },
  {
    type: '7.6m',
    count: 3,
    capacity: 1500,
    fixed_cost: 500,
    fuel_consumption_per_100km: 18,
    avg_speed_kmh: 50,
    color: '#16A34A',
    emission_kg_per_km: 0.4,
  },
  {
    type: '9.6m',
    count: 2,
    capacity: 2500,
    fixed_cost: 800,
    fuel_consumption_per_100km: 25,
    avg_speed_kmh: 55,
    color: '#D97706',
    emission_kg_per_km: 0.55,
  },
];

const DEFAULT_PARAMS: SolverParams = {
  fuel_price: 7.5,
  hourly_wage: 50,
  carbon_price: 0.08,
  late_penalty_per_min: 10,
  search_time_limit: 30,
  use_multi_strategy: true,
  use_parallel: true,
  strategy_weights: {
    min_distance: 0.25,
    min_vehicles: 0.25,
    min_cost: 0.25,
    min_emission: 0.25,
  },
};

export interface SolverState {
  customers: Customer[];
  params: SolverParams;
  vehicleConfig: VehicleSpec[];
  currentSolution: SolveResponse | null;
  comparisonResults: SolveResponse[];
  setCustomers: (customers: Customer[]) => void;
  setParams: (params: Partial<SolverParams>) => void;
  setVehicleConfig: (config: VehicleSpec[]) => void;
  setCurrentSolution: (solution: SolveResponse | null) => void;
  addComparisonResult: (solution: SolveResponse) => void;
  removeComparisonResult: (index: number) => void;
  clearComparisonResults: () => void;
  loadSampleData: () => void;
}

export const useSolverStore = create<SolverState>()(
  persist(
    (set) => ({
      customers: [],
      params: DEFAULT_PARAMS,
      vehicleConfig: DEFAULT_VEHICLE_CONFIG,
      currentSolution: null,
      comparisonResults: [],
      setCustomers: (customers) => set({ customers }),
      setParams: (params) =>
        set((state) => ({ params: { ...state.params, ...params } })),
      setVehicleConfig: (vehicleConfig) => set({ vehicleConfig }),
      setCurrentSolution: (currentSolution) => set({ currentSolution }),
      addComparisonResult: (solution) =>
        set((state) => ({
          comparisonResults: [...state.comparisonResults, solution],
        })),
      removeComparisonResult: (index) =>
        set((state) => ({
          comparisonResults: state.comparisonResults.filter(
            (_, i) => i !== index
          ),
        })),
      clearComparisonResults: () => set({ comparisonResults: [] }),
      loadSampleData: () =>
        set({
          customers: [
            {
              id: 0,
              name: '仓库',
              lat: 39.9042,
              lon: 116.4074,
              demand: 0,
              service_time_min: 0,
              tw_earliest: 0,
              tw_latest: 1440,
              is_depot: true,
            },
            {
              id: 1,
              name: '客户A',
              lat: 39.9142,
              lon: 116.4174,
              demand: 50,
              service_time_min: 15,
              tw_earliest: 480,
              tw_latest: 720,
            },
            {
              id: 2,
              name: '客户B',
              lat: 39.9242,
              lon: 116.3974,
              demand: 80,
              service_time_min: 20,
              tw_earliest: 540,
              tw_latest: 780,
            },
            {
              id: 3,
              name: '客户C',
              lat: 39.8942,
              lon: 116.4274,
              demand: 30,
              service_time_min: 10,
              tw_earliest: 600,
              tw_latest: 840,
            },
          ],
        }),
    }),
    { name: 'greenvrp-solver-storage' }
  )
);
