import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Truck, FileDown, GitCompare, BarChart3 } from 'lucide-react';
import { Link } from 'react-router-dom';

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">工作台</h1>
        <p className="text-muted-foreground">快速进入 GreenVRP 核心功能</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              总求解次数
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">0</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              已保存场景
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">0</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              累计节省里程
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">0 km</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              累计减少碳排
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">0 kg</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Button asChild className="h-auto flex-col items-start gap-2 p-4">
          <Link to="/workspace">
            <Truck className="h-5 w-5" />
            <span className="text-base">求解工作台</span>
          </Link>
        </Button>
        <Button
          asChild
          variant="secondary"
          className="h-auto flex-col items-start gap-2 p-4"
        >
          <Link to="/workspace/scenarios">
            <FileDown className="h-5 w-5" />
            <span className="text-base">场景管理</span>
          </Link>
        </Button>
        <Button
          asChild
          variant="secondary"
          className="h-auto flex-col items-start gap-2 p-4"
        >
          <Link to="/workspace/comparison">
            <GitCompare className="h-5 w-5" />
            <span className="text-base">方案对比</span>
          </Link>
        </Button>
        <Button
          asChild
          variant="secondary"
          className="h-auto flex-col items-start gap-2 p-4"
        >
          <Link to="/analytics/cost">
            <BarChart3 className="h-5 w-5" />
            <span className="text-base">成本分析</span>
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>最近活动</CardTitle>
          <CardDescription>暂无最近活动</CardDescription>
        </CardHeader>
        <CardContent className="flex h-32 items-center justify-center text-muted-foreground">
          开始使用求解工作台创建您的第一个优化方案
        </CardContent>
      </Card>
    </div>
  );
}
