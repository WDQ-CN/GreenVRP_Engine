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
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useSolverStore } from '@/stores/solverStore';
import type { SolveResponse } from '@/types';

const ComparisonCharts = lazy(() =>
  import('@/components/charts/ComparisonCharts').then((m) => ({
    default: m.ComparisonCharts,
  }))
);

function formatCurrency(value: number): string {
  return `¥${value.toFixed(2)}`;
}

function formatDistance(value: number): string {
  return `${value.toFixed(1)} km`;
}

function formatCO2(value: number): string {
  return `${value.toFixed(2)} kg`;
}

function resultLabel(index: number): string {
  return `方案 ${index + 1}`;
}

export function ComparisonPage() {
  const {
    currentSolution,
    comparisonResults,
    addComparisonResult,
    removeComparisonResult,
    clearComparisonResults,
  } = useSolverStore();

  const items: SolveResponse[] = currentSolution
    ? [currentSolution, ...comparisonResults]
    : comparisonResults;

  const handleAddCurrent = () => {
    if (currentSolution) {
      addComparisonResult(currentSolution);
    }
  };

  if (items.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">方案对比</h1>
          <p className="text-muted-foreground">对比不同求解策略与场景的结果</p>
        </div>
        <Card>
          <CardContent className="flex h-80 flex-col items-center justify-center gap-4 text-muted-foreground">
            <p>暂无对比数据，请先在“求解工作台”执行求解</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const bestCost = Math.min(
    ...items.map((item) => item.cost_result?.total_cost ?? Infinity)
  );
  const bestDistance = Math.min(
    ...items.map((item) => item.cost_result?.total_distance_km ?? Infinity)
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">方案对比</h1>
          <p className="text-muted-foreground">对比不同求解策略与场景的结果</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={handleAddCurrent}
            disabled={!currentSolution}
          >
            加入当前方案
          </Button>
          <Button
            variant="outline"
            onClick={clearComparisonResults}
            disabled={comparisonResults.length === 0 && !currentSolution}
          >
            清空对比
          </Button>
        </div>
      </div>

      <Suspense
        fallback={
          <Card>
            <CardContent className="flex h-72 items-center justify-center text-muted-foreground">
              加载图表…
            </CardContent>
          </Card>
        }
      >
        <ComparisonCharts items={items} />
      </Suspense>

      <Card>
        <CardHeader>
          <CardTitle>详细数据</CardTitle>
          <CardDescription>各方案核心指标一览</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>方案</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">总成本</TableHead>
                <TableHead className="text-right">总里程</TableHead>
                <TableHead className="text-right">车辆数</TableHead>
                <TableHead className="text-right">碳排放</TableHead>
                <TableHead className="text-right">迟到</TableHead>
                <TableHead className="text-right">求解时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item, index) => {
                const cost = item.cost_result;
                const isBestCost = cost && cost.total_cost === bestCost;
                const isBestDistance =
                  cost && cost.total_distance_km === bestDistance;
                return (
                  <TableRow key={index}>
                    <TableCell className="font-medium">
                      {resultLabel(index)}
                      {index === 0 && currentSolution && (
                        <Badge variant="secondary" className="ml-2">
                          当前
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          item.status === 'completed' ? 'success' : 'outline'
                        }
                      >
                        {item.status === 'completed' ? '完成' : item.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {isBestCost && (
                        <Badge variant="success" className="mr-2">
                          最优
                        </Badge>
                      )}
                      {formatCurrency(cost?.total_cost ?? 0)}
                    </TableCell>
                    <TableCell className="text-right">
                      {isBestDistance && (
                        <Badge variant="success" className="mr-2">
                          最优
                        </Badge>
                      )}
                      {formatDistance(cost?.total_distance_km ?? 0)}
                    </TableCell>
                    <TableCell className="text-right">
                      {item.solution?.routes.length ?? 0}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCO2(cost?.carbon_emission_kg ?? 0)}
                    </TableCell>
                    <TableCell className="text-right">
                      {item.solution?.total_late_minutes ?? 0} 分
                    </TableCell>
                    <TableCell className="text-right">
                      {item.solution?.solve_time_seconds.toFixed(2) ?? '-'} 秒
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          const comparisonIndex = currentSolution
                            ? index - 1
                            : index;
                          if (comparisonIndex >= 0) {
                            removeComparisonResult(comparisonIndex);
                          }
                        }}
                        disabled={index === 0 && Boolean(currentSolution)}
                      >
                        移除
                      </Button>
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
