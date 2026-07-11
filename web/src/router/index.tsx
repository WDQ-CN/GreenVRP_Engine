import { Suspense, lazy } from 'react';
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from 'react-router-dom';

import { AppShell } from '@/components/layout/AppShell';
import { PageLoader } from '@/components/PageLoader';
// 首屏路由直接同步加载，减少初始请求瀑布与 LCP
import { DashboardPage } from '@/pages/DashboardPage';

const ComparisonPage = lazy(() =>
  import('@/pages/ComparisonPage').then((m) => ({ default: m.ComparisonPage }))
);
const CostAnalysisPage = lazy(() =>
  import('@/pages/CostAnalysisPage').then((m) => ({
    default: m.CostAnalysisPage,
  }))
);
const RoutesPage = lazy(() =>
  import('@/pages/RoutesPage').then((m) => ({ default: m.RoutesPage }))
);
const ScenariosPage = lazy(() =>
  import('@/pages/ScenariosPage').then((m) => ({ default: m.ScenariosPage }))
);
const SettingsPage = lazy(() =>
  import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage }))
);
const VehiclesPage = lazy(() =>
  import('@/pages/VehiclesPage').then((m) => ({ default: m.VehiclesPage }))
);
const WorkspacePage = lazy(() =>
  import('@/pages/WorkspacePage').then((m) => ({ default: m.WorkspacePage }))
);

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'workspace', element: <WorkspacePage /> },
      { path: 'workspace/scenarios', element: <ScenariosPage /> },
      { path: 'workspace/comparison', element: <ComparisonPage /> },
      { path: 'analytics/cost', element: <CostAnalysisPage /> },
      { path: 'analytics/routes', element: <RoutesPage /> },
      { path: 'analytics/vehicles', element: <VehiclesPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]);

export function Router() {
  return (
    <Suspense fallback={<PageLoader />}>
      <RouterProvider router={router} />
    </Suspense>
  );
}
