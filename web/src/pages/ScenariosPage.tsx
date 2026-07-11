import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, FolderOpen, Loader2 } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  createScenario,
  deleteScenario,
  getScenario,
  listScenarios,
  vehicleConfigMapToArray,
} from '@/lib/scenarios';
import { buildSolverParams, buildVehicleConfigMap } from '@/lib/solver';
import { useSolverStore } from '@/stores/solverStore';

export function ScenariosPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const {
    customers,
    params,
    vehicleConfig,
    setCustomers,
    setParams,
    setVehicleConfig,
  } = useSolverStore();
  const { data: scenarios = [], isLoading } = useQuery({
    queryKey: ['scenarios'],
    queryFn: listScenarios,
  });
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      await createScenario({
        name: name.trim(),
        description: description.trim() || undefined,
        customers,
        vehicle_config: buildVehicleConfigMap(vehicleConfig),
        params: buildSolverParams(params),
      });
      setOpen(false);
      setName('');
      setDescription('');
      await queryClient.invalidateQueries({ queryKey: ['scenarios'] });
    } finally {
      setSubmitting(false);
    }
  };

  const handleLoad = async (id: number) => {
    const detail = await getScenario(id);
    setCustomers(detail.customers);
    if (detail.params) {
      setParams({
        fuel_price: detail.params.fuel_price,
        hourly_wage: detail.params.hourly_wage,
        carbon_price: detail.params.carbon_price,
        late_penalty_per_min: detail.params.late_penalty_per_min,
        search_time_limit: detail.params.search_time_limit,
        use_multi_strategy: detail.params.use_multi_strategy,
        use_parallel: detail.params.use_parallel,
      });
    }
    if (detail.vehicle_config) {
      setVehicleConfig(vehicleConfigMapToArray(detail.vehicle_config));
    }
    navigate('/workspace');
  };

  const handleDelete = async (id: number) => {
    await deleteScenario(id);
    await queryClient.invalidateQueries({ queryKey: ['scenarios'] });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">场景管理</h1>
          <p className="text-muted-foreground">
            保存、加载和管理工作台场景配置
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <Plus className="mr-1 h-4 w-4" />
          保存当前场景
        </Button>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          加载中...
        </div>
      ) : scenarios.length === 0 ? (
        <Card>
          <CardContent className="flex h-64 flex-col items-center justify-center gap-4 text-muted-foreground">
            <FolderOpen className="h-10 w-10" />
            <p>暂无保存的场景</p>
            <Button variant="outline" onClick={() => setOpen(true)}>
              保存当前配置为场景
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {scenarios.map((scenario) => (
            <Card key={scenario.id}>
              <CardHeader>
                <CardTitle className="text-lg">{scenario.name}</CardTitle>
                <CardDescription>
                  {scenario.description || '无描述'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>{scenario.customer_count} 客户</span>
                  <span>{scenario.solution_count} 方案</span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleLoad(scenario.id)}
                  >
                    加载到工作台
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(scenario.id)}
                    aria-label="删除场景"
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>保存场景</DialogTitle>
            <DialogDescription>
              将当前客户数据、参数和车型配置保存为一个场景。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="scenario-name">场景名称</Label>
              <Input
                id="scenario-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：北京城区配送方案 A"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="scenario-description">描述</Label>
              <Textarea
                id="scenario-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="可选：描述该场景的特点"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!name.trim() || submitting}
            >
              {submitting && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
