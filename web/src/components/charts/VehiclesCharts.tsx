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

type UsageItem = {
  type: string;
  count: number;
  distance: number;
  demand: number;
  capacity: number;
};

const COLORS = ['#2563EB', '#16A34A', '#D97706', '#DC2626', '#0891B2'];

interface Props {
  usageData: UsageItem[];
}

export function VehiclesCharts({ usageData }: Props) {
  const pieData = usageData.map((item) => ({
    name: item.type,
    value: item.count,
  }));

  const barData = usageData.map((item) => ({
    type: item.type,
    使用次数: item.count,
    平均里程: item.count > 0 ? item.distance / item.count : 0,
  }));

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>车型使用次数</CardTitle>
          <CardDescription>各车型被分配的车辆数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={(entry) => `${entry.name}: ${entry.value} 辆`}
                >
                  {pieData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>车辆使用统计</CardTitle>
          <CardDescription>使用次数与平均里程</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Bar yAxisId="left" dataKey="使用次数" fill="#2563EB" />
                <Bar yAxisId="right" dataKey="平均里程" fill="#16A34A" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
