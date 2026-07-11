import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
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
import type { SolveResponse } from '@/types';

interface Props {
  items: SolveResponse[];
}

function resultLabel(index: number): string {
  return `方案 ${index + 1}`;
}

export function ComparisonCharts({ items }: Props) {
  const chartData = items.map((item, index) => ({
    name: resultLabel(index),
    总成本: item.cost_result?.total_cost ?? 0,
    碳排放: item.cost_result?.carbon_emission_kg ?? 0,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>指标对比</CardTitle>
        <CardDescription>总成本与碳排放对比</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis
                yAxisId="left"
                tickFormatter={(value) => `¥${value.toFixed(0)}`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tickFormatter={(value) => `${value.toFixed(0)} kg`}
              />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="总成本" fill="#2563EB" />
              <Bar yAxisId="right" dataKey="碳排放" fill="#16A34A" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
