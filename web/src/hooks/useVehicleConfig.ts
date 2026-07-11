import { useCallback } from 'react';
import { useSolverStore } from '@/stores/solverStore';
import type { VehicleSpec } from '@/types';

/**
 * 车辆配置管理 Hook
 *
 * 封装对车辆配置的访问和操作，组件不直接访问 Zustand store。
 */
export function useVehicleConfig() {
  const vehicleConfig = useSolverStore((s) => s.vehicleConfig);
  const setVehicleConfig = useSolverStore((s) => s.setVehicleConfig);

  const vehicleCount = vehicleConfig.reduce(
    (sum, v) => sum + (v.count || 1),
    0
  );

  return {
    vehicleConfig,
    setVehicleConfig: useCallback(
      (config: VehicleSpec[]) => setVehicleConfig(config),
      [setVehicleConfig]
    ),
    vehicleCount,
  } as const;
}
