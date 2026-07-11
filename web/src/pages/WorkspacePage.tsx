import { useCallback, useState } from 'react';
import { Play, Loader2, Pause } from 'lucide-react';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { CustomerDataPanel } from '@/components/workspace/CustomerDataPanel';
import { SolverParamsPanel } from '@/components/workspace/SolverParamsPanel';
import { VehicleConfigPanel } from '@/components/workspace/VehicleConfigPanel';
import { ResultsPanel } from '@/components/workspace/ResultsPanel';
import { useCustomers } from '@/hooks/useCustomers';
import { useSolver } from '@/hooks/useSolver';
import { useVehicleConfig } from '@/hooks/useVehicleConfig';
import { useSolverParams } from '@/hooks/useSolverParams';
import { useSolveExecution } from '@/hooks/useSolveExecution';
import type { SolveResponse } from '@/types';

export function WorkspacePage() {
  const { customers, setCustomers, loadSampleData } = useCustomers();
  const { vehicleConfig, setVehicleConfig } = useVehicleConfig();
  const { params, setParams } = useSolverParams();
  const { currentSolution, setCurrentSolution } = useSolver();
  const [activeTab, setActiveTab] = useState('customers');
  const [useAsync, setUseAsync] = useState(true);

  const onSolveComplete = useCallback(
    (response: SolveResponse) => {
      setCurrentSolution(response);
      setActiveTab('results');
    },
    [setCurrentSolution]
  );

  const { loading, error, progress, handleSolve, handleCancel } =
    useSolveExecution({ onComplete: onSolveComplete });

  const progressText =
    progress !== null ? `${Math.round(progress)}%` : undefined;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">求解工作台</h1>
        <p className="text-muted-foreground">
          配置参数、导入客户数据并执行路径优化
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>求解错误</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <aside className="space-y-6 lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle>参数配置</CardTitle>
              <CardDescription>油价、时薪、碳价、求解时间等</CardDescription>
            </CardHeader>
            <CardContent>
              <SolverParamsPanel params={params} onParamsChange={setParams} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>车型配置</CardTitle>
              <CardDescription>4.2m / 7.6m / 9.6m 车辆</CardDescription>
            </CardHeader>
            <CardContent>
              <VehicleConfigPanel
                vehicleConfig={vehicleConfig}
                onConfigChange={setVehicleConfig}
              />
            </CardContent>
          </Card>
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="space-y-0.5">
              <Label htmlFor="async-mode" className="text-sm font-medium">
                异步求解
              </Label>
              <p className="text-xs text-muted-foreground">支持长任务轮询</p>
            </div>
            <Switch
              id="async-mode"
              checked={useAsync}
              onCheckedChange={setUseAsync}
              disabled={loading}
            />
          </div>

          <Button
            className="w-full gap-2"
            size="lg"
            onClick={() =>
              handleSolve(customers, vehicleConfig, params, useAsync)
            }
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {loading
              ? progressText
                ? `求解中 ${progressText}`
                : '求解中...'
              : '开始求解'}
          </Button>

          {loading && useAsync && (
            <Button
              variant="outline"
              className="w-full gap-2"
              onClick={handleCancel}
            >
              <Pause className="h-4 w-4" />
              取消求解
            </Button>
          )}
        </aside>

        <section className="lg:col-span-9">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="customers">客户数据</TabsTrigger>
              <TabsTrigger value="results">求解结果</TabsTrigger>
            </TabsList>
            <TabsContent value="customers">
              <Card>
                <CardHeader>
                  <CardTitle>客户数据</CardTitle>
                  <CardDescription>支持 CSV 导入与手动编辑</CardDescription>
                </CardHeader>
                <CardContent>
                  <CustomerDataPanel
                    customers={customers}
                    onCustomersChange={setCustomers}
                    onLoadSampleData={loadSampleData}
                  />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="results">
              <Card>
                <CardHeader>
                  <CardTitle>求解结果</CardTitle>
                  <CardDescription>地图、路线与成本分析</CardDescription>
                </CardHeader>
                <CardContent>
                  {currentSolution ? (
                    <ResultsPanel
                      solution={currentSolution}
                      customers={customers}
                    />
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      暂无求解结果，请先配置参数并执行求解
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </section>
      </div>
    </div>
  );
}
