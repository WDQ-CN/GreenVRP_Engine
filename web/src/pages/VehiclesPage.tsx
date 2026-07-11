import { Suspense, lazy } from 'react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useSolverStore } from '@/stores/solverStore';

const VehiclesCharts = lazy(() =>
  import('@/components/charts/VehiclesCharts').then((m) => ({
    default: m.VehiclesCharts,
  }))
);

function formatDistance(value: number): string {
  return `${value.toFixed(1)} km`;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function VehiclesPage() {
  const { currentSolution, vehicleConfig } = useSolverStore();

  if (!currentSolution?.solution) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">车辆使用</h1>
          <p className="text-muted-foreground">车辆利用率与载重分析</p>
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

  const vehicleUsage = routes.reduce(
    (acc, route) => {
      const type = route.vehicle_type;
      if (!acc[type]) {
        acc[type] = { type, count: 0, distance: 0, demand: 0, capacity: 0 };
      }
      acc[type].count += 1;
      acc[type].distance += route.distance_km;
      acc[type].demand += route.total_demand;
      return acc;
    },
    {} as Record<
      string,
      {
        type: string;
        count: number;
        distance: number;
        demand: number;
        capacity: number;
      }
    >
  );

  Object.values(vehicleUsage).forEach((item) => {
    const config = vehicleConfig.find((v) => v.type === item.type);
    item.capacity = (config?.capacity ?? 1) * item.count;
  });

  const usageData = Object.values(vehicleUsage);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">车辆使用</h1>
        <p className="text-muted-foreground">车辆利用率与载重分析</p>
      </div>

      <Suspense
        fallback={
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardContent className="flex h-64 items-center justify-center text-muted-foreground">
                加载图表…
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex h-64 items-center justify-center text-muted-foreground">
                加载图表…
              </CardContent>
            </Card>
          </div>
        }
      >
        <VehiclesCharts usageData={usageData} />
      </Suspense>

      <Card>
        <CardHeader>
          <CardTitle>车辆使用明细</CardTitle>
          <CardDescription>每辆车的载重、里程与利用率</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>车辆</TableHead>
                <TableHead className="text-right">车型</TableHead>
                <TableHead className="text-right">里程</TableHead>
                <TableHead className="text-right">载重</TableHead>
                <TableHead className="text-right">容量</TableHead>
                <TableHead className="text-right">利用率</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {routes.map((route) => {
                const config = vehicleConfig.find(
                  (v) => v.type === route.vehicle_type
                );
                const capacity = config?.capacity ?? 1;
                const utilization =
                  capacity > 0 ? route.total_demand / capacity : 0;
                return (
                  <TableRow key={route.vehicle_id}>
                    <TableCell className="font-medium">
                      #{route.vehicle_id}
                    </TableCell>
                    <TableCell className="text-right">
                      {route.vehicle_type}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatDistance(route.distance_km)}
                    </TableCell>
                    <TableCell className="text-right">
                      {route.total_demand} kg
                    </TableCell>
                    <TableCell className="text-right">{capacity} kg</TableCell>
                    <TableCell className="text-right">
                      {formatPercent(utilization)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
