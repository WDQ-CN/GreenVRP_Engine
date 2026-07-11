import { memo, useCallback, useMemo } from 'react';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import type { SolverParams } from '@/types';

const PARAM_FIELDS: {
  key: 'fuel_price' | 'hourly_wage' | 'carbon_price' | 'late_penalty_per_min';
  label: string;
  step: string;
  min: number;
}[] = [
  { key: 'fuel_price', label: '油价 (元/升)', step: '0.1', min: 0 },
  { key: 'hourly_wage', label: '司机时薪 (元/小时)', step: '1', min: 0 },
  { key: 'carbon_price', label: '碳价 (元/kg)', step: '0.01', min: 0 },
  {
    key: 'late_penalty_per_min',
    label: '迟到惩罚 (元/分钟)',
    step: '1',
    min: 0,
  },
];

const DEFAULT_WEIGHTS = {
  min_distance: 0.25,
  min_vehicles: 0.25,
  min_cost: 0.25,
  min_emission: 0.25,
} as const;

interface SolverParamsPanelProps {
  params: SolverParams;
  onParamsChange: (params: Partial<SolverParams>) => void;
}

function SolverParamsPanelInner({
  params,
  onParamsChange,
}: SolverParamsPanelProps) {
  const weights = useMemo(
    () => params.strategy_weights ?? DEFAULT_WEIGHTS,
    [params.strategy_weights]
  );

  const updateWeight = useCallback(
    (key: string, value: number) => {
      const currentWeights = params.strategy_weights ?? DEFAULT_WEIGHTS;
      onParamsChange({
        strategy_weights: {
          ...currentWeights,
          [key]: value,
        },
      });
    },
    [onParamsChange, params.strategy_weights]
  );

  return (
    <div className="space-y-5">
      {PARAM_FIELDS.map((field) => (
        <div key={field.key} className="space-y-1.5">
          <Label htmlFor={field.key} className="text-xs">
            {field.label}
          </Label>
          <Input
            id={field.key}
            type="number"
            min={field.min}
            step={field.step}
            value={params[field.key]}
            onChange={(e) =>
              onParamsChange({ [field.key]: Number(e.target.value) })
            }
          />
        </div>
      ))}

      <div className="space-y-1.5">
        <Label htmlFor="search_time_limit" className="text-xs">
          求解时间限制 (秒)
        </Label>
        <Input
          id="search_time_limit"
          type="number"
          min={1}
          step={1}
          value={params.search_time_limit}
          onChange={(e) =>
            onParamsChange({ search_time_limit: Number(e.target.value) })
          }
        />
      </div>

      <div className="flex items-center justify-between">
        <Label htmlFor="use_multi_strategy" className="text-xs">
          启用多策略
        </Label>
        <Switch
          id="use_multi_strategy"
          checked={params.use_multi_strategy}
          onCheckedChange={(checked) =>
            onParamsChange({ use_multi_strategy: checked })
          }
        />
      </div>

      <div className="flex items-center justify-between">
        <Label htmlFor="use_parallel" className="text-xs">
          并行求解
        </Label>
        <Switch
          id="use_parallel"
          checked={params.use_parallel}
          onCheckedChange={(checked) =>
            onParamsChange({ use_parallel: checked })
          }
        />
      </div>

      {params.use_multi_strategy && (
        <div className="space-y-3 rounded-md border p-3">
          <p className="text-xs font-medium text-muted-foreground">策略权重</p>
          {Object.entries(weights).map(([key, value]) => (
            <div key={key} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span>{key}</span>
                <span className="text-muted-foreground">
                  {(value * 100).toFixed(0)}%
                </span>
              </div>
              <Slider
                value={[value]}
                min={0}
                max={1}
                step={0.05}
                onValueChange={([v]) => updateWeight(key, v)}
                aria-label={`${key} 权重`}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const SolverParamsPanel = memo(SolverParamsPanelInner);
