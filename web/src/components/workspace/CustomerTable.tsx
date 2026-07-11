import { useMemo, useState } from 'react';
import { Trash2, Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import type { Customer } from '@/types';

interface CustomerTableProps {
  customers: Customer[];
  onChange: (customers: Customer[]) => void;
}

const FIELDS: {
  key: keyof Customer;
  label: string;
  width: string;
  type?: string;
}[] = [
  { key: 'id', label: 'ID', width: 'w-16', type: 'number' },
  { key: 'name', label: '名称', width: 'w-32' },
  { key: 'lat', label: '纬度', width: 'w-28', type: 'number' },
  { key: 'lon', label: '经度', width: 'w-28', type: 'number' },
  { key: 'demand', label: '需求', width: 'w-20', type: 'number' },
  { key: 'service_time_min', label: '服务(分)', width: 'w-24', type: 'number' },
  { key: 'tw_earliest', label: '最早', width: 'w-20', type: 'number' },
  { key: 'tw_latest', label: '最晚', width: 'w-20', type: 'number' },
];

export function CustomerTable({ customers, onChange }: CustomerTableProps) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const depot = useMemo(
    () => customers.find((c) => c.is_depot) || null,
    [customers]
  );

  const updateCustomer = (id: number, key: keyof Customer, value: unknown) => {
    onChange(
      customers.map((c) => {
        if (c.id !== id) return c;
        if (key === 'name' || key === 'is_depot') {
          return { ...c, [key]: value };
        }
        const num = typeof value === 'string' ? Number(value) : value;
        return { ...c, [key]: Number.isNaN(num) ? 0 : num };
      })
    );
  };

  const deleteSelected = () => {
    onChange(customers.filter((c) => !selectedIds.has(c.id)));
    setSelectedIds(new Set());
  };

  const addCustomer = () => {
    const maxId = customers.reduce((max, c) => Math.max(max, c.id), 0);
    const newCustomer: Customer = {
      id: maxId + 1,
      name: `客户${maxId + 1}`,
      lat: 39.9,
      lon: 116.4,
      demand: 10,
      service_time_min: 15,
      tw_earliest: 480,
      tw_latest: 720,
    };
    onChange([...customers, newCustomer]);
  };

  const toggleSelect = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === customers.length && customers.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(customers.map((c) => c.id)));
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            共 {customers.length} 个节点
          </span>
          {depot && (
            <Badge variant="outline" className="text-xs">
              仓库: {depot.name}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {selectedIds.size > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={deleteSelected}
              className="gap-1"
            >
              <Trash2 className="h-4 w-4" />
              删除选中 ({selectedIds.size})
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={addCustomer}>
            <Plus className="mr-1 h-4 w-4" />
            添加客户
          </Button>
        </div>
      </div>

      <div className="overflow-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="w-10 px-2 py-2">
                <input
                  type="checkbox"
                  checked={
                    customers.length > 0 &&
                    selectedIds.size === customers.length
                  }
                  onChange={toggleSelectAll}
                  aria-label="全选"
                  className="h-4 w-4 rounded border-gray-300"
                />
              </th>
              {FIELDS.map((field) => (
                <th
                  key={field.key}
                  className={`px-2 py-2 text-left font-medium text-muted-foreground ${field.width}`}
                >
                  {field.label}
                </th>
              ))}
              <th className="px-2 py-2 text-left font-medium text-muted-foreground">
                仓库
              </th>
            </tr>
          </thead>
          <tbody>
            {customers.map((customer) => (
              <tr
                key={customer.id}
                className={
                  customer.is_depot ? 'bg-primary/5' : 'hover:bg-muted/30'
                }
              >
                <td className="px-2 py-1.5">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(customer.id)}
                    onChange={() => toggleSelect(customer.id)}
                    aria-label={`选择 ${customer.name}`}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                </td>
                {FIELDS.map((field) => (
                  <td key={field.key} className="px-2 py-1.5">
                    <Input
                      type={field.type === 'number' ? 'number' : 'text'}
                      value={(customer[field.key] as string | number) ?? ''}
                      onChange={(e) =>
                        updateCustomer(customer.id, field.key, e.target.value)
                      }
                      className="h-7 min-w-0 border-0 bg-transparent px-1 py-0 shadow-none focus:bg-background focus:ring-1"
                      aria-label={`${customer.name} ${field.label}`}
                    />
                  </td>
                ))}
                <td className="px-2 py-1.5">
                  <input
                    type="checkbox"
                    checked={!!customer.is_depot}
                    onChange={(e) =>
                      updateCustomer(customer.id, 'is_depot', e.target.checked)
                    }
                    aria-label={`${customer.name} 设为仓库`}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
