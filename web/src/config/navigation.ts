import {
  BarChart3,
  FolderOpen,
  GitCompare,
  LayoutDashboard,
  Map,
  PieChart,
  Settings,
  Truck,
} from 'lucide-react';

export interface NavItem {
  label: string;
  path: string;
  icon: typeof LayoutDashboard;
  group?: string;
}

export const navigation: NavItem[] = [
  { label: '工作台', path: '/', icon: LayoutDashboard, group: '核心' },
  { label: '求解工作台', path: '/workspace', icon: Truck, group: '核心' },
  {
    label: '场景管理',
    path: '/workspace/scenarios',
    icon: FolderOpen,
    group: '核心',
  },
  {
    label: '成本分析',
    path: '/analytics/cost',
    icon: BarChart3,
    group: '分析',
  },
  { label: '路线详情', path: '/analytics/routes', icon: Map, group: '分析' },
  {
    label: '车辆使用',
    path: '/analytics/vehicles',
    icon: PieChart,
    group: '分析',
  },
  {
    label: '方案对比',
    path: '/workspace/comparison',
    icon: GitCompare,
    group: '分析',
  },
  { label: '设置', path: '/settings', icon: Settings, group: '系统' },
];
