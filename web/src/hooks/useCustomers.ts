import { useSolverStore } from '@/stores/solverStore';

/**
 * 客户数据管理 Hook
 *
 * 封装对客户数据的操作，组件不直接访问 Zustand store。
 * 切换状态管理库时只需修改此文件。
 */
export function useCustomers() {
  const customers = useSolverStore((s) => s.customers);
  const setCustomers = useSolverStore((s) => s.setCustomers);
  const loadSampleData = useSolverStore((s) => s.loadSampleData);

  const hasDepot = customers.some((c) => c.is_depot);
  const customerCount = customers.filter((c) => !c.is_depot).length;
  const totalDemand = customers.reduce((sum, c) => sum + (c.demand || 0), 0);

  return {
    customers,
    setCustomers,
    loadSampleData,
    hasDepot,
    customerCount,
    totalDemand,
  } as const;
}
