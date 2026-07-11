import type { Customer, Route } from '@/types';

interface RouteMapProps {
  customers: Customer[];
  routes: Route[];
  width?: number;
  height?: number;
}

export function RouteMap({
  customers,
  routes,
  width = 600,
  height = 360,
}: RouteMapProps) {
  if (customers.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border bg-muted/20 text-sm text-muted-foreground"
        style={{ height }}
      >
        暂无客户数据
      </div>
    );
  }

  const lats = customers.map((c) => c.lat);
  const lons = customers.map((c) => c.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);

  const padding = 24;
  const xScale = (lon: number) =>
    padding + ((lon - minLon) / (maxLon - minLon || 1)) * (width - padding * 2);
  const yScale = (lat: number) =>
    height -
    padding -
    ((lat - minLat) / (maxLat - minLat || 1)) * (height - padding * 2);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full rounded-md border bg-muted/20"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="路线地图"
    >
      {routes.map((route, routeIndex) => {
        const points = route.stops
          .map((stop) => {
            const customer = customers.find((c) => c.id === stop.customer_id);
            if (!customer) return null;
            return `${xScale(customer.lon)},${yScale(customer.lat)}`;
          })
          .filter(Boolean)
          .join(' ');

        return (
          <g key={routeIndex}>
            <title>{`${route.vehicle_type} #${route.vehicle_id} 路线`}</title>
            <polyline
              points={points}
              fill="none"
              stroke={route.vehicle_color}
              strokeWidth={2}
              strokeOpacity={0.7}
            />
          </g>
        );
      })}

      {customers.map((customer) => {
        const cx = xScale(customer.lon);
        const cy = yScale(customer.lat);
        const isDepot = customer.is_depot;
        return (
          <g key={customer.id}>
            <title>
              {isDepot ? `仓库: ${customer.name}` : `客户: ${customer.name}`}
            </title>
            <circle
              cx={cx}
              cy={cy}
              r={isDepot ? 6 : 4}
              fill={isDepot ? '#2563EB' : '#16A34A'}
              stroke="white"
              strokeWidth={1.5}
            />
            {!isDepot && (
              <text
                x={cx + 8}
                y={cy + 4}
                fontSize={10}
                fill="currentColor"
                className="text-muted-foreground"
              >
                {customer.name}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
