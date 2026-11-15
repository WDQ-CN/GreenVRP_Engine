import { DIESEL_CO2_FACTOR, ROUTE_PALETTE } from "./data"
import { bearing, roadKm } from "./geo"
import type {
  Baseline,
  CostResult,
  Customer,
  RoutePlan,
  SolveOutcome,
  SolveSolution,
  SolverSettings,
  Stop,
  VehicleConfigMap,
  VehicleSpec,
  VehicleType,
} from "./types"

const DEPART_MINUTE = 480
const LOAD_FUEL_EMPTY_RATIO = 0.75
const LOAD_FUEL_FULL_RATIO = 1.25

interface RouteTotals {
  driving: number
  waiting: number
  service: number
}

function routeFuelLiters(route: RoutePlan, spec: VehicleSpec): number {
  const totalDemand = route.stops
    .filter((stop) => stop.customer_id !== 0 && stop.customer_id !== null)
    .reduce((sum, stop) => sum + stop.demand, 0)
  if (totalDemand <= 0 || route.stops.length < 2) {
    return (route.distance_km / 100) * spec.fuel_per_100km
  }

  const capacity = Math.max(route.capacity, 1)
  let load = totalDemand
  let liters = 0
  for (let index = 0; index < route.stops.length - 1; index += 1) {
    const from = route.stops[index]
    const to = route.stops[index + 1]
    if (from.customer_id !== 0 && from.customer_id !== null) {
      load = Math.max(0, load - from.demand)
    }
    const loadRatio = Math.min(1, Math.max(0, load / capacity))
    const fuelPer100km =
      spec.fuel_per_100km *
      (LOAD_FUEL_EMPTY_RATIO + (LOAD_FUEL_FULL_RATIO - LOAD_FUEL_EMPTY_RATIO) * loadRatio)
    liters += (roadKm(from, to) / 100) * fuelPer100km
  }
  return liters
}

function nearestOrder(group: Customer[], depot: Customer, spec: VehicleSpec) {
  const remaining = [...group]
  const ordered: Customer[] = []
  let cursor: Customer = depot
  let clock = DEPART_MINUTE
  while (remaining.length > 0) {
    let best = 0
    let bestScore = Infinity
    remaining.forEach((candidate, index) => {
      const distance = roadKm(cursor, candidate)
      const arrival = clock + (distance / spec.speed_kmh) * 60
      const late = Math.max(0, arrival - candidate.tw_latest)
      const score = distance + late * 0.65
      if (score < bestScore) {
        bestScore = score
        best = index
      }
    })
    const next = remaining.splice(best, 1)[0]
    ordered.push(next)
    const travel = (roadKm(cursor, next) / spec.speed_kmh) * 60
    const arrival = clock + travel
    clock = Math.max(arrival, next.tw_earliest) + next.service_time_min
    cursor = next
  }
  return ordered
}

function buildRoute(
  index: number,
  group: Customer[],
  type: VehicleType,
  spec: VehicleSpec,
  depot: Customer,
): { route: RoutePlan; totals: RouteTotals } {
  const ordered = nearestOrder(group, depot, spec)
  const totals: RouteTotals = { driving: 0, waiting: 0, service: 0 }
  const stops: Stop[] = [
    {
      node: 0,
      customer_id: 0,
      customer_name: depot.name,
      lat: depot.lat,
      lon: depot.lon,
      demand: 0,
      service_time: 0,
      arrival_time: DEPART_MINUTE,
      departure_time: DEPART_MINUTE,
      tw_earliest: depot.tw_earliest,
      tw_latest: depot.tw_latest,
      late_minutes: 0,
      is_late: false,
    },
  ]
  let clock = DEPART_MINUTE
  let distance = 0
  let lateMinutes = 0
  let demand = 0
  let cursor: Customer = depot

  ordered.forEach((customer) => {
    const leg = roadKm(cursor, customer)
    distance += leg
    totals.driving += (leg / spec.speed_kmh) * 60
    const travel = (leg / spec.speed_kmh) * 60
    const arrival = clock + travel
    const wait = Math.max(0, customer.tw_earliest - arrival)
    const departure = Math.max(arrival, customer.tw_earliest) + customer.service_time_min
    const late = Math.max(0, arrival - customer.tw_latest)
    totals.waiting += wait
    totals.service += customer.service_time_min
    lateMinutes += late
    demand += customer.demand
    stops.push({
      node: stops.length,
      customer_id: customer.id,
      customer_name: customer.name,
      lat: customer.lat,
      lon: customer.lon,
      demand: customer.demand,
      service_time: customer.service_time_min,
      arrival_time: Math.round(arrival),
      departure_time: Math.round(departure),
      tw_earliest: customer.tw_earliest,
      tw_latest: customer.tw_latest,
      late_minutes: Math.round(late),
      is_late: late > 0,
    })
    clock = departure
    cursor = customer
  })

  const returnLeg = roadKm(cursor, depot)
  distance += returnLeg
  totals.driving += (returnLeg / spec.speed_kmh) * 60
  const returnTime = clock + (returnLeg / spec.speed_kmh) * 60
  stops.push({
    node: 0,
    customer_id: null,
    customer_name: `${depot.name} · 返程`,
    lat: depot.lat,
    lon: depot.lon,
    demand: 0,
    service_time: 0,
    arrival_time: Math.round(returnTime),
    departure_time: Math.round(returnTime),
  })

  return {
    route: {
      vehicle_id: index,
      vehicle_type: type,
      vehicle_color: spec.color || ROUTE_PALETTE[index % ROUTE_PALETTE.length],
      capacity: spec.capacity,
      stops,
      distance_km: Math.round(distance * 10) / 10,
      total_demand: demand,
      total_time_min: Math.round(returnTime - DEPART_MINUTE),
      late_minutes: Math.round(lateMinutes),
    },
    totals,
  }
}

interface Centroid {
  lat: number
  lon: number
}

function meanPoint(group: Customer[]): Centroid {
  return {
    lat: group.reduce((sum, customer) => sum + customer.lat, 0) / group.length,
    lon: group.reduce((sum, customer) => sum + customer.lon, 0) / group.length,
  }
}

function squaredDistance(a: Centroid, b: Centroid): number {
  const latScale = Math.cos((a.lat * Math.PI) / 180)
  const dLat = a.lat - b.lat
  const dLon = (a.lon - b.lon) * latScale
  return dLat * dLat + dLon * dLon
}

function groupByFleet(
  deliveries: Customer[],
  fleet: VehicleType[],
  vehicles: VehicleConfigMap,
  depot: Customer,
): Array<{ type: VehicleType; group: Customer[] }> {
  const routeCount = fleet.length
  const seeded = [...deliveries].sort((a, b) => bearing(depot, a) - bearing(depot, b))
  let centroids: Centroid[] = Array.from({ length: routeCount }, (_, index) => {
    const point = seeded[Math.floor(((index + 0.5) * seeded.length) / routeCount)]
    return { lat: point.lat, lon: point.lon }
  })
  let groups: Customer[][] = []

  for (let iteration = 0; iteration < 14; iteration += 1) {
    groups = Array.from({ length: routeCount }, () => [])
    deliveries.forEach((customer) => {
      let closest = 0
      let closestDistance = Infinity
      centroids.forEach((centroid, index) => {
        const distance = squaredDistance(centroid, customer)
        if (distance < closestDistance) {
          closestDistance = distance
          closest = index
        }
      })
      groups[closest].push(customer)
    })

    const emptyIndex = groups.findIndex((group) => group.length === 0)
    if (emptyIndex >= 0) {
      let farthest: Customer | null = null
      let farthestDistance = -1
      for (let groupIndex = 0; groupIndex < groups.length; groupIndex += 1) {
        for (const customer of groups[groupIndex]) {
          const distance = squaredDistance(centroids[groupIndex], customer)
          if (distance > farthestDistance) {
            farthestDistance = distance
            farthest = customer
          }
        }
      }
      if (farthest) {
        centroids[emptyIndex] = { lat: farthest.lat, lon: farthest.lon }
        continue
      }
    }

    const next = groups.map(meanPoint)
    const movement = next.reduce(
      (sum, point, index) =>
        sum + Math.abs(point.lat - centroids[index].lat) + Math.abs(point.lon - centroids[index].lon),
      0,
    )
    centroids = next
    if (movement < 0.0004) break
  }

  const weighted = groups
    .filter((group) => group.length > 0)
    .map((group) => ({
      group,
      demand: group.reduce((sum, customer) => sum + customer.demand, 0),
    }))
    .sort((a, b) => b.demand - a.demand)
  const available = [...fleet].sort((a, b) => vehicles[b].capacity - vehicles[a].capacity)

  return weighted.map((entry, index) => ({ type: available[index], group: entry.group }))
}

export function buildBaseline(
  customers: Customer[],
  routes: RoutePlan[],
  vehicles: VehicleConfigMap,
): Baseline {
  const depot = customers.find((c) => c.id === 0) ?? customers[0]
  const deliveries = customers.filter((c) => c.id !== 0)
  const distance = deliveries.reduce((sum, c) => sum + roadKm(depot, c) * 2, 0)
  const avgFuel =
    routes.length > 0
      ? routes.reduce((sum, r) => sum + vehicles[r.vehicle_type].fuel_per_100km, 0) /
        routes.length
      : (Object.values(vehicles)[0]?.fuel_per_100km ?? 12)
  return {
    distance_km: Math.round(distance * 10) / 10,
    carbon_kg: Math.round((distance / 100) * avgFuel * DIESEL_CO2_FACTOR * 10) / 10,
  }
}

export function solveDemo(
  customers: Customer[],
  vehicles: VehicleConfigMap,
  settings: SolverSettings,
): SolveOutcome {
  const startedAt = performance.now()
  const depot = customers.find((c) => c.id === 0) ?? customers[0]
  const deliveries = customers.filter((c) => c.id !== 0)
  const fleet: VehicleType[] = []
  Object.keys(vehicles).forEach((type) => {
    for (let index = 0; index < vehicles[type].count; index += 1) fleet.push(type)
  })

  if (fleet.length === 0) {
    throw new Error("车队可用车辆为 0，请至少启用一种车型。")
  }

  fleet.sort((a, b) => vehicles[b].capacity - vehicles[a].capacity)
  const activeFleet = fleet.slice(0, Math.min(fleet.length, deliveries.length))
  const groups = groupByFleet(deliveries, activeFleet, vehicles, depot)
  const routes: RoutePlan[] = []
  const totalsList: RouteTotals[] = []

  groups.forEach(({ type, group }, index) => {
    const built = buildRoute(index, group, type, vehicles[type], depot)
    routes.push(built.route)
    totalsList.push(built.totals)
  })

  const driving = totalsList.reduce((s, t) => s + t.driving, 0)
  const waiting = totalsList.reduce((s, t) => s + t.waiting, 0)
  const service = totalsList.reduce((s, t) => s + t.service, 0)
  const totalDistance = routes.reduce((s, r) => s + r.distance_km, 0)
  const routeFuels = routes.map((route) =>
    routeFuelLiters(route, vehicles[route.vehicle_type]),
  )
  const transport = routeFuels.reduce(
    (sum, liters) => sum + liters * settings.fuel_price,
    0,
  )
  const carbon = routeFuels.reduce(
    (sum, liters) => sum + liters * DIESEL_CO2_FACTOR,
    0,
  )
  const fixed = routes.reduce((s, r) => s + vehicles[r.vehicle_type].fixed_cost, 0)
  const lateMinutes = routes.reduce((s, r) => s + r.late_minutes, 0)
  const penalty = lateMinutes * settings.late_penalty_per_min
  const labor = ((driving + waiting + service) / 60) * settings.hourly_wage
  const carbonCost = carbon * settings.carbon_price
  const totalCost = transport + labor + fixed + penalty + carbonCost

  const cost: CostResult = {
    transport_cost: Math.round(transport * 100) / 100,
    labor_cost: Math.round(labor * 100) / 100,
    fixed_cost: Math.round(fixed * 100) / 100,
    penalty_cost: Math.round(penalty * 100) / 100,
    carbon_cost: Math.round(carbonCost * 100) / 100,
    total_cost: Math.round(totalCost * 100) / 100,
    carbon_emission_kg: Math.round(carbon * 100) / 100,
    total_distance_km: Math.round(totalDistance * 100) / 100,
    total_time_min: Math.round(driving + waiting + service),
    driving_time_min: Math.round(driving * 10) / 10,
    service_time_min: Math.round(service * 10) / 10,
    waiting_time_min: Math.round(waiting * 10) / 10,
    cost_breakdown: {
      运输变动成本: Math.round(transport * 100) / 100,
      人工时间成本: Math.round(labor * 100) / 100,
      车辆固定成本: Math.round(fixed * 100) / 100,
      违约惩罚成本: Math.round(penalty * 100) / 100,
      碳排放成本: Math.round(carbonCost * 100) / 100,
    },
  }

  const vehiclesUsed: Partial<Record<VehicleType, number>> = {}
  routes.forEach((r) => {
    vehiclesUsed[r.vehicle_type] = (vehiclesUsed[r.vehicle_type] ?? 0) + 1
  })

  const solution: SolveSolution = {
    routes,
    total_distance: Math.round(totalDistance * 100) / 100,
    vehicles_used: vehiclesUsed,
    total_late_minutes: lateMinutes,
    solution_status: "SUCCESS",
    solve_time_seconds: Math.round((performance.now() - startedAt) * 10) / 10000,
  }

  return {
    solution,
    cost,
    customers,
    baseline: buildBaseline(customers, routes, vehicles),
    source: "demo",
    solvedAt: new Date().toISOString(),
    note: `内置 ${deliveries.length} 个配送节点 · 贪心构造演示，非 OR-Tools 结果`,
  }
}
