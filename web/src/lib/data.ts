import type {
  Customer,
  SolverPreset,
  SolverSettings,
  VehicleConfigMap,
  VehicleSpec,
} from "./types"

export const MAX_FLEET_SIZE = 15

export const VEHICLE_SPEC_FIELDS = [
  { key: "capacity", label: "载重", suffix: "件", min: 1, max: 20000, step: 1, decimals: 0 },
  { key: "fixed_cost", label: "发车成本", suffix: "元", min: 0, max: 100000, step: 1, decimals: 0 },
  { key: "fuel_per_100km", label: "百公里油耗", suffix: "L", min: 0, max: 100, step: 0.1, decimals: 1 },
  { key: "speed_kmh", label: "平均速度", suffix: "km/h", min: 1, max: 120, step: 1, decimals: 0 },
] as const

export type VehicleSpecField = (typeof VEHICLE_SPEC_FIELDS)[number]["key"]

export const DEFAULT_SETTINGS: SolverSettings = {
  fuel_price: 7.5,
  hourly_wage: 50,
  carbon_price: 0.08,
  late_penalty_per_min: 10,
  search_time_limit: 45,
  use_multi_strategy: true,
  use_parallel: true,
}

export const DEFAULT_VEHICLES: VehicleConfigMap = {
  "4.2m": {
    label: "4.2m 小型车",
    color: "hsl(var(--lime))",
    capacity: 800,
    fixed_cost: 200,
    fuel_per_100km: 12,
    speed_kmh: 40,
    count: 5,
  },
  "7.6m": {
    label: "7.6m 中型车",
    color: "hsl(var(--mint))",
    capacity: 1500,
    fixed_cost: 350,
    fuel_per_100km: 18,
    speed_kmh: 35,
    count: 3,
  },
  "9.6m": {
    label: "9.6m 大型车",
    color: "hsl(var(--amber))",
    capacity: 2500,
    fixed_cost: 500,
    fuel_per_100km: 25,
    speed_kmh: 30,
    count: 2,
  },
}

const NAMED_CUSTOMERS: Customer[] = [
  { id: 0, name: "中心仓", lat: 39.9042, lon: 116.4074, demand: 0, service_time_min: 0, tw_earliest: 480, tw_latest: 1080 },
  { id: 1, name: "望京站", lat: 39.9962, lon: 116.4709, demand: 60, service_time_min: 15, tw_earliest: 480, tw_latest: 720 },
  { id: 2, name: "中关村站", lat: 39.9836, lon: 116.3163, demand: 45, service_time_min: 12, tw_earliest: 500, tw_latest: 700 },
  { id: 3, name: "国贸站", lat: 39.9085, lon: 116.461, demand: 80, service_time_min: 20, tw_earliest: 480, tw_latest: 620 },
  { id: 4, name: "亦庄站", lat: 39.795, lon: 116.506, demand: 95, service_time_min: 20, tw_earliest: 540, tw_latest: 800 },
  { id: 5, name: "通州站", lat: 39.909, lon: 116.656, demand: 70, service_time_min: 18, tw_earliest: 560, tw_latest: 820 },
  { id: 6, name: "石景山站", lat: 39.914, lon: 116.222, demand: 55, service_time_min: 15, tw_earliest: 600, tw_latest: 840 },
  { id: 7, name: "丰台站", lat: 39.858, lon: 116.286, demand: 65, service_time_min: 15, tw_earliest: 480, tw_latest: 680 },
  { id: 8, name: "顺义站", lat: 40.13, lon: 116.654, demand: 50, service_time_min: 15, tw_earliest: 600, tw_latest: 860 },
  { id: 9, name: "大兴站", lat: 39.726, lon: 116.338, demand: 75, service_time_min: 18, tw_earliest: 520, tw_latest: 780 },
  { id: 10, name: "昌平站", lat: 40.22, lon: 116.231, demand: 40, service_time_min: 12, tw_earliest: 620, tw_latest: 900 },
  { id: 11, name: "朝阳站", lat: 39.921, lon: 116.49, demand: 85, service_time_min: 20, tw_earliest: 500, tw_latest: 700 },
  { id: 12, name: "海淀站", lat: 39.958, lon: 116.298, demand: 60, service_time_min: 15, tw_earliest: 480, tw_latest: 740 },
  { id: 13, name: "酒仙桥站", lat: 39.968, lon: 116.493, demand: 55, service_time_min: 15, tw_earliest: 480, tw_latest: 760 },
  { id: 14, name: "北苑站", lat: 40.041, lon: 116.418, demand: 50, service_time_min: 15, tw_earliest: 500, tw_latest: 800 },
  { id: 15, name: "西三旗站", lat: 40.063, lon: 116.348, demand: 45, service_time_min: 12, tw_earliest: 540, tw_latest: 840 },
  { id: 16, name: "五道口站", lat: 39.992, lon: 116.337, demand: 40, service_time_min: 12, tw_earliest: 480, tw_latest: 780 },
  { id: 17, name: "六里桥站", lat: 39.879, lon: 116.296, demand: 60, service_time_min: 15, tw_earliest: 480, tw_latest: 740 },
  { id: 18, name: "卢沟桥站", lat: 39.856, lon: 116.216, demand: 40, service_time_min: 12, tw_earliest: 600, tw_latest: 920 },
  { id: 19, name: "马家堡站", lat: 39.842, lon: 116.367, demand: 55, service_time_min: 15, tw_earliest: 520, tw_latest: 800 },
  { id: 20, name: "方庄站", lat: 39.866, lon: 116.434, demand: 65, service_time_min: 18, tw_earliest: 560, tw_latest: 860 },
  { id: 21, name: "双井站", lat: 39.897, lon: 116.457, demand: 70, service_time_min: 18, tw_earliest: 480, tw_latest: 720 },
  { id: 22, name: "十里河站", lat: 39.865, lon: 116.48, demand: 60, service_time_min: 15, tw_earliest: 520, tw_latest: 820 },
  { id: 23, name: "常营站", lat: 39.928, lon: 116.599, demand: 50, service_time_min: 15, tw_earliest: 600, tw_latest: 920 },
  { id: 24, name: "天通苑站", lat: 40.075, lon: 116.415, demand: 75, service_time_min: 20, tw_earliest: 540, tw_latest: 840 },
]

const EXTRA_SITES: Array<[name: string, lat: number, lon: number]> = [
  ["东直门站", 39.942, 116.435],
  ["西直门站", 39.941, 116.355],
  ["三里屯站", 39.934, 116.454],
  ["团结湖站", 39.934, 116.461],
  ["呼家楼站", 39.923, 116.462],
  ["亮马桥站", 39.949, 116.468],
  ["亚运村站", 39.994, 116.41],
  ["健翔桥站", 39.983, 116.378],
  ["来广营站", 40.02, 116.47],
  ["孙河站", 40.05, 116.53],
  ["崔各庄站", 40.02, 116.52],
  ["金盏站", 40.0, 116.58],
  ["东坝站", 39.97, 116.55],
  ["豆各庄站", 39.87, 116.56],
  ["黑庄户站", 39.86, 116.6],
  ["次渠站", 39.8, 116.58],
  ["台湖站", 39.83, 116.63],
  ["马驹桥站", 39.76, 116.55],
  ["旧宫站", 39.81, 116.47],
  ["小红门站", 39.83, 116.47],
  ["十八里店站", 39.85, 116.49],
  ["垡头站", 39.87, 116.51],
  ["百子湾站", 39.9, 116.49],
  ["高碑店站", 39.91, 116.53],
  ["定福庄站", 39.92, 116.56],
  ["管庄站", 39.91, 116.59],
  ["八里桥站", 39.905, 116.62],
  ["果园站", 39.9, 116.64],
  ["梨园站", 39.88, 116.64],
  ["九棵树站", 39.89, 116.63],
  ["张家湾站", 39.86, 116.65],
  ["宋庄站", 39.95, 116.65],
  ["后沙峪站", 40.08, 116.56],
  ["南法信站", 40.12, 116.61],
  ["牛栏山站", 40.17, 116.63],
  ["空港站", 40.08, 116.6],
  ["新国展站", 40.07, 116.52],
  ["四季青站", 39.96, 116.24],
  ["田村站", 39.94, 116.25],
  ["永定路站", 39.92, 116.26],
  ["青塔站", 39.89, 116.27],
  ["岳各庄站", 39.88, 116.29],
  ["长辛店站", 39.82, 116.22],
  ["良乡站", 39.75, 116.22],
  ["长阳站", 39.78, 116.23],
  ["五棵松站", 39.91, 116.28],
  ["万寿路站", 39.91, 116.31],
  ["公主坟站", 39.91, 116.33],
  ["军博站", 39.91, 116.34],
  ["复兴门站", 39.91, 116.36],
  ["西单站", 39.91, 116.38],
  ["王府井站", 39.91, 116.41],
  ["东单站", 39.91, 116.42],
  ["崇文门站", 39.9, 116.42],
  ["前门站", 39.9, 116.4],
  ["天桥站", 39.89, 116.4],
  ["陶然亭站", 39.88, 116.39],
  ["菜户营站", 39.87, 116.36],
  ["丽泽站", 39.86, 116.34],
  ["看丹桥站", 39.84, 116.3],
  ["总部基地站", 39.82, 116.29],
  ["花乡站", 39.82, 116.33],
  ["新发地站", 39.81, 116.35],
  ["西红门站", 39.79, 116.35],
  ["黄村站", 39.75, 116.34],
  ["清源路站", 39.74, 116.34],
  ["高米店站", 39.77, 116.33],
  ["枣园站", 39.76, 116.36],
  ["杨庄站", 39.93, 116.22],
  ["八角站", 39.92, 116.22],
  ["鲁谷站", 39.91, 116.23],
  ["清河站", 40.033, 116.33],
  ["上地站", 40.03, 116.31],
  ["西二旗站", 40.05, 116.3],
  ["回龙观站", 40.075, 116.34],
  ["霍营站", 40.08, 116.37],
]

// 稳定的伪随机属性，保证每次刷新看到同一份 100 节点数据。
function hashSeed(value: string): number {
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0) || 1
}

function createGeneratedCustomer(
  id: number,
  [name, lat, lon]: [string, number, number],
): Customer {
  let seed = hashSeed(name)
  const next = () => {
    seed = (seed * 48271) % 2147483647
    return seed / 2147483647
  }
  const demand = 30 + Math.round(next() * 9) * 5
  const earliest = 480 + Math.floor(next() * 7) * 20
  const latest = Math.min(960, earliest + 240 + Math.floor(next() * 4) * 20)
  return {
    id,
    name,
    lat,
    lon,
    demand,
    service_time_min: demand >= 65 ? 15 : demand >= 45 ? 12 : 10,
    tw_earliest: earliest,
    tw_latest: latest,
  }
}

export const DEMO_CUSTOMERS: Customer[] = [
  ...NAMED_CUSTOMERS,
  ...EXTRA_SITES.map((site, index) =>
    createGeneratedCustomer(NAMED_CUSTOMERS.length + index, site),
  ),
]

export const VEHICLE_LABEL: Record<string, string> = {
  "4.2m": "4.2m 小型车",
  "7.6m": "7.6m 中型车",
  "9.6m": "9.6m 大型车",
}

export const ROUTE_COLOR: Record<string, string> = {
  "4.2m": "hsl(var(--lime))",
  "7.6m": "hsl(var(--mint))",
  "9.6m": "hsl(var(--amber))",
}

export const ROUTE_PALETTE = [
  "hsl(var(--lime))",
  "hsl(var(--mint))",
  "hsl(var(--amber))",
  "hsl(var(--sky))",
  "hsl(8 62% 64%)",
  "hsl(268 42% 70%)",
  "hsl(178 36% 58%)",
  "hsl(30 82% 64%)",
  "hsl(330 48% 70%)",
  "hsl(96 32% 60%)",
  "hsl(210 55% 70%)",
  "hsl(45 68% 68%)",
  "hsl(190 45% 68%)",
  "hsl(320 35% 64%)",
  "hsl(150 35% 66%)",
] as const

export function vehicleLabel(type: string, spec?: VehicleSpec): string {
  return spec?.label || VEHICLE_LABEL[type] || type
}

export function vehicleColor(
  type: string,
  spec?: VehicleSpec,
  fallbackIndex = 0,
): string {
  return (
    spec?.color ||
    ROUTE_COLOR[type] ||
    ROUTE_PALETTE[fallbackIndex % ROUTE_PALETTE.length]
  )
}

export const COST_ROWS = [
  { key: "运输变动成本", color: "hsl(var(--lime))" },
  { key: "人工时间成本", color: "hsl(var(--mint))" },
  { key: "车辆固定成本", color: "hsl(var(--sky))" },
  { key: "违约惩罚成本", color: "hsl(var(--amber))" },
  { key: "碳排放成本", color: "hsl(var(--moss))" },
] as const

export const PRESETS: Record<
  SolverPreset,
  { label: string; hint: string; settings: Partial<SolverSettings> }
> = {
  balanced: {
    label: "均衡方案",
    hint: "成本 · 时间 · 碳排",
    settings: { carbon_price: 0.08, late_penalty_per_min: 10, search_time_limit: 45 },
  },
  carbon: {
    label: "低碳优先",
    hint: "提高碳价权重",
    settings: { carbon_price: 0.24, late_penalty_per_min: 10, search_time_limit: 90 },
  },
  speed: {
    label: "时效优先",
    hint: "收紧迟到罚金",
    settings: { carbon_price: 0.08, late_penalty_per_min: 24, search_time_limit: 20 },
  },
}

export const DIESEL_CO2_FACTOR = 2.63

export const DEMO_API_BASE = "http://localhost:8000"
export const DEMO_API_KEY = "green-vrp-default-key-2024"
