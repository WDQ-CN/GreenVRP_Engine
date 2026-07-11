import { memo } from 'react';
import { RouteMap } from './RouteMap';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { Customer, SolveResponse } from '@/types';

interface ResultsPanelProps {
  solution: SolveResponse;
  customers: Customer[];
}

function formatCurrency(value: number): string {
  return `¥${value.toFixed(2)}`;
}

function formatDistance(value: number): string {
  return `${value.toFixed(1)} km`;
}

function formatEmission(value: number): string {
  return `${value.toFixed(2)} kg`;
}

function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.floor(minutes % 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

function ResultsPanelInner({ solution, customers }: ResultsPanelProps) {
  if (!solution || !solution.solution || !solution.cost_result) {
    return (
      <div className="flex h-80 items-center justify-center text-muted-foreground">
        尚未执行求解，请在左侧配置参数并点击"开始求解"
      </div>
    );
  }

  const { routes } = solution.solution;
  const cost = solution.cost_result;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              总成本
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">
              {formatCurrency(cost.total_cost)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              总里程
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">
              {formatDistance(cost.total_distance_km)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              碳排放
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold text-green-600">
              {formatEmission(cost.carbon_emission_kg)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              车辆数
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{routes.length}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>路线地图</CardTitle>
        </CardHeader>
        <CardContent>
          <RouteMap customers={customers} routes={routes} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>路线详情</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {routes.map((route, index) => (
            <div key={index} className="rounded-md border p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: route.vehicle_color }}
                    aria-label={`${route.vehicle_type} 路线颜色`}
                  />
                  <span className="font-medium">
                    {route.vehicle_type} #{route.vehicle_id}
                  </span>
                </div>
                <Badge variant="outline">
                  {Math.max(0, route.stops.length - 1)} 客户
                </Badge>
              </div>
              <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span>里程: {formatDistance(route.distance_km)}</span>
                <span>载重: {route.total_demand} kg</span>
                <span>耗时: {route.total_time_min} 分</span>
              </div>
              <Separator className="my-2" />
              <div className="space-y-1 text-sm">
                {route.stops.map((stop, stopIndex) => (
                  <div key={stopIndex} className="flex items-center gap-2">
                    <span className="w-6 text-right text-muted-foreground">
                      {stopIndex + 1}
                    </span>
                    <span className="flex-1">{stop.customer_name}</span>
                    <span className="text-xs text-muted-foreground">
                      {stop.arrival_time !== null
                        ? minutesToTime(stop.arrival_time)
                        : '-'}
                    </span>
                    {stop.is_late && (
                      <Badge variant="destructive" className="text-[10px]">
                        迟到 {stop.late_minutes} 分
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export const ResultsPanel = memo(ResultsPanelInner);
