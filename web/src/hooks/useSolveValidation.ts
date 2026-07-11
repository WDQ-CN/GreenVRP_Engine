import { useCallback } from 'react';
import type { Customer } from '@/types';

/**
 * 求解输入验证 Hook
 *
 * 在发起求解前验证客户数据的完整性。
 * 职责单一：只做验证，不处理求解逻辑。
 */
export function useSolveValidation() {
  const validate = useCallback((customers: Customer[]): string | null => {
    const depot = customers.find((c) => c.is_depot);
    if (!depot) {
      return '请至少设置一个仓库节点（is_depot=true）';
    }
    if (customers.length < 2) {
      return '请至少添加一个仓库和一个客户';
    }
    return null;
  }, []);

  return { validate } as const;
}
