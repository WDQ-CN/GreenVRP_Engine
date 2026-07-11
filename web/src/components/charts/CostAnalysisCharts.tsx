import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

type Route = {
  vehicle_id: number;
  vehicle_type: string;
  distance_km: number;
  total_demand: number;
};

type CostResult = {
  transport_cost: number;
  labor_cost: number;
  fixed_cost: number;
  penalty_cost: number;
  carbon_cost: number;
  total_distance_km: number;
};

const COLORS = ['#2563EB', '#16A34A', '#D97706', '#DC2626', '#0891B2'];

function formatCurrency(value: number): string {
  return `¥${value.toFixed(2)}`;
}

interface Props {
  cost: CostResult;
  routes: Route[];
}

export function CostAnalysisCharts({ cost, routes }: Props) {
  const costBreakdown = [
    { name: '运输成本', value: cost.transport_cost },
    { name: '人工成本', value: cost.labor_cost },
    { name: '固定成本', value: cost.fixed_cost },
    { name: '惩罚成本', value: cost.penalty_cost },
    { name: '碳排成本', value: cost.carbon_cost },
  ];

  const routeCostData = routes.map((route) => ({
    vehicle: `${route.vehicle_type} #${route.vehicle_id}`,
    固定成本: route.distance_km > 0 ? cost.fixed_cost / routes.length : 0,
    运输成本:
      cost.transport_cost * (route.distance_km / (cost.total_distance_km || 1)),
    碳排成本:
      cost.carbon_cost * (route.distance_km / (cost.total_distance_km || 1)),
  }));

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>成本构成</CardTitle>
          <CardDescription>各项成本占比</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={costBreakdown}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={(entry) =>
                    `${entry.name}: ${formatCurrency(entry.value)}`
                  }
                >
                  {costBreakdown.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>成本明细</CardTitle>
          <CardDescription>按车辆与路线拆分</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={routeCostData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="vehicle" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={(value) => `¥${value.toFixed(0)}`} />
                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                <Legend />
                <Bar dataKey="固定成本" stackId="a" fill="#2563EB" />
                <Bar dataKey="运输成本" stackId="a" fill="#16A34A" />
                <Bar dataKey="碳排成本" stackId="a" fill="#D97706" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
