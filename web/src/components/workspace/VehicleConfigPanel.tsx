import { memo } from 'react';
import { Plus, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { VehicleSpec } from '@/types';

interface VehicleConfigPanelProps {
  vehicleConfig: VehicleSpec[];
  onConfigChange: (config: VehicleSpec[]) => void;
}

const VEHICLE_FIELDS: {
  key: keyof VehicleSpec;
  label: string;
  step: string;
  type?: string;
}[] = [
  { key: 'type', label: '车型', step: '1', type: 'text' },
  { key: 'count', label: '数量', step: '1', type: 'number' },
  { key: 'capacity', label: '载重 (kg)', step: '1', type: 'number' },
  { key: 'fixed_cost', label: '固定成本 (元)', step: '1', type: 'number' },
  {
    key: 'fuel_consumption_per_100km',
    label: '油耗 (L/100km)',
    step: '0.1',
    type: 'number',
  },
  { key: 'avg_speed_kmh', label: '平均速度 (km/h)', step: '1', type: 'number' },
  {
    key: 'emission_kg_per_km',
    label: '碳排 (kg/km)',
    step: '0.01',
    type: 'number',
  },
];

function VehicleConfigPanelInner({
  vehicleConfig,
  onConfigChange,
}: VehicleConfigPanelProps) {
  const updateVehicle = (
    index: number,
    key: keyof VehicleSpec,
    value: unknown
  ) => {
    const next = vehicleConfig.map((v, i) => {
      if (i !== index) return v;
      if (key === 'type' || key === 'color') {
        return { ...v, [key]: value };
      }
      const num = typeof value === 'string' ? Number(value) : value;
      return { ...v, [key]: Number.isNaN(num) ? 0 : num };
    });
    onConfigChange(next);
  };

  const addVehicle = () => {
    onConfigChange([
      ...vehicleConfig,
      {
        type: '新车型',
        count: 1,
        capacity: 1000,
        fixed_cost: 400,
        fuel_consumption_per_100km: 15,
        avg_speed_kmh: 45,
        color: '#6B7280',
        emission_kg_per_km: 0.3,
      },
    ]);
  };

  const removeVehicle = (index: number) => {
    onConfigChange(vehicleConfig.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      {vehicleConfig.map((vehicle, index) => (
        <div key={index} className="space-y-2 rounded-md border p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{vehicle.type}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => removeVehicle(index)}
              aria-label={`删除 ${vehicle.type}`}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {VEHICLE_FIELDS.map((field) => (
              <div key={field.key} className="space-y-1">
                <Label
                  htmlFor={`vehicle-${index}-${field.key}`}
                  className="text-[10px] text-muted-foreground"
                >
                  {field.label}
                </Label>
                <Input
                  id={`vehicle-${index}-${field.key}`}
                  type={field.type}
                  step={field.step}
                  value={vehicle[field.key]}
                  onChange={(e) =>
                    updateVehicle(index, field.key, e.target.value)
                  }
                  className="h-7 text-xs"
                />
              </div>
            ))}
            <div className="space-y-1">
              <Label
                htmlFor={`vehicle-${index}-color`}
                className="text-[10px] text-muted-foreground"
              >
                颜色
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id={`vehicle-${index}-color`}
                  type="color"
                  value={vehicle.color}
                  onChange={(e) =>
                    updateVehicle(index, 'color', e.target.value)
                  }
                  className="h-7 w-10 cursor-pointer p-1"
                />
                <span className="text-xs text-muted-foreground">
                  {vehicle.color}
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}

      <Button
        variant="outline"
        size="sm"
        className="w-full"
        onClick={addVehicle}
      >
        <Plus className="mr-1 h-4 w-4" />
        添加车型
      </Button>
    </div>
  );
}

export const VehicleConfigPanel = memo(VehicleConfigPanelInner);
