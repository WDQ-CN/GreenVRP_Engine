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

const CostAnalysisCharts = lazy(() =>
  import('@/components/charts/CostAnalysisCharts').then((m) => ({
    default: m.CostAnalysisCharts,
  }))
);

function formatCurrency(value: number): string {
  return `¥${value.toFixed(2)}`;
}

function formatCO2(value: number): string {
  return `${value.toFixed(2)} kg`;
}

function formatDistance(value: number): string {
  return `${value.toFixed(1)} km`;
}

export function CostAnalysisPage() {
  const { currentSolution } = useSolverStore();

  if (!currentSolution?.solution || !currentSolution?.cost_result) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">成本分析</h1>
          <p className="text-muted-foreground">
            总成本、固定成本、燃油成本、碳排放构成
          </p>
        </div>
        <Card>
          <CardContent className="flex h-80 items-center justify-center text-muted-foreground">
            暂无求解结果，请先在“求解工作台”执行求解
          </CardContent>
        </Card>
      </div>
    );
  }

  const cost = currentSolution.cost_result;
  const routes = currentSolution.solution.routes;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">成本分析</h1>
        <p className="text-muted-foreground">
          总成本、固定成本、燃油成本、碳排放构成
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              总成本
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
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
            <div className="text-2xl font-bold">
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
            <div className="text-2xl font-bold text-green-600">
              {formatCO2(cost.carbon_emission_kg)}
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
            <div className="text-2xl font-bold">{routes.length}</div>
          </CardContent>
        </Card>
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
        <CostAnalysisCharts cost={cost} routes={routes} />
      </Suspense>

      <Card>
        <CardHeader>
          <CardTitle>路线成本明细</CardTitle>
          <CardDescription>每辆车的里程、载重与分摊成本</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>车辆</TableHead>
                <TableHead className="text-right">里程</TableHead>
                <TableHead className="text-right">载重</TableHead>
                <TableHead className="text-right">固定成本</TableHead>
                <TableHead className="text-right">运输成本</TableHead>
                <TableHead className="text-right">碳排成本</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {routes.map((route) => {
                const fixedCost =
                  route.distance_km > 0 ? cost.fixed_cost / routes.length : 0;
                const transportCost =
                  cost.transport_cost *
                  (route.distance_km / (cost.total_distance_km || 1));
                const carbonCost =
                  cost.carbon_cost *
                  (route.distance_km / (cost.total_distance_km || 1));
                return (
                  <TableRow key={route.vehicle_id}>
                    <TableCell className="font-medium">
                      {route.vehicle_type} #{route.vehicle_id}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatDistance(route.distance_km)}
                    </TableCell>
                    <TableCell className="text-right">
                      {route.total_demand} kg
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(fixedCost)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(transportCost)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(carbonCost)}
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
