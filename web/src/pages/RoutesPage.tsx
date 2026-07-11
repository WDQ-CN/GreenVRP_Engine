import { MapPin, Truck } from 'lucide-react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { RouteMap } from '@/components/workspace/RouteMap';
import { useSolverStore } from '@/stores/solverStore';

function formatDistance(value: number): string {
  return `${value.toFixed(1)} km`;
}

function minutesToTime(minutes: number | null): string {
  if (minutes === null) return '-';
  const h = Math.floor(minutes / 60);
  const m = Math.floor(minutes % 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

export function RoutesPage() {
  const { customers, currentSolution } = useSolverStore();

  if (!currentSolution?.solution) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">路线详情</h1>
          <p className="text-muted-foreground">地图展示与路线停靠点明细</p>
        </div>
        <Card>
          <CardContent className="flex h-80 items-center justify-center text-muted-foreground">
            暂无求解结果，请先在“求解工作台”执行求解
          </CardContent>
        </Card>
      </div>
    );
  }

  const routes = currentSolution.solution.routes;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">路线详情</h1>
        <p className="text-muted-foreground">地图展示与路线停靠点明细</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>路线地图</CardTitle>
          <CardDescription>车辆路线可视化</CardDescription>
        </CardHeader>
        <CardContent>
          <RouteMap customers={customers} routes={routes} height={480} />
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {routes.map((route, index) => (
          <Card key={index}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Truck className="h-4 w-4 text-muted-foreground" />
                  <CardTitle className="text-base">
                    {route.vehicle_type} #{route.vehicle_id}
                  </CardTitle>
                </div>
                <Badge variant="outline">{route.stops.length - 1} 客户</Badge>
              </div>
              <CardDescription>
                里程 {formatDistance(route.distance_km)} · 载重{' '}
                {route.total_demand} kg · 耗时 {route.total_time_min} 分
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {route.stops.map((stop, stopIndex) => (
                  <div key={stopIndex}>
                    <div className="flex items-start gap-3">
                      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">
                        {stopIndex + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">
                            {stop.customer_name}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {minutesToTime(stop.arrival_time)}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          需求 {stop.demand} kg · 服务 {stop.service_time} 分
                          {stop.is_late && (
                            <span className="ml-2 text-destructive">
                              迟到 {stop.late_minutes} 分
                            </span>
                          )}
                        </div>
                      </div>
                      {stopIndex === 0 ||
                      stopIndex === route.stops.length - 1 ? (
                        <MapPin className="h-4 w-4 text-blue-500" />
                      ) : null}
                    </div>
                    {stopIndex < route.stops.length - 1 && (
                      <Separator className="my-3 ml-9" />
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
