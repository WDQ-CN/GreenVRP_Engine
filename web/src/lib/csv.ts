import type { Customer } from '@/types';

const HEADER_MAP: Record<string, keyof Customer> = {
  id: 'id',
  编号: 'id',
  name: 'name',
  名称: 'name',
  客户名称: 'name',
  lat: 'lat',
  纬度: 'lat',
  lon: 'lon',
  经度: 'lon',
  demand: 'demand',
  需求量: 'demand',
  service_time_min: 'service_time_min',
  服务时间: 'service_time_min',
  service_time: 'service_time_min',
  tw_earliest: 'tw_earliest',
  时间窗最早: 'tw_earliest',
  earliest: 'tw_earliest',
  tw_latest: 'tw_latest',
  时间窗最晚: 'tw_latest',
  latest: 'tw_latest',
  is_depot: 'is_depot',
  是否仓库: 'is_depot',
  depot: 'is_depot',
};

function normalizeHeader(header: string): string {
  return header
    .trim()
    .replace(/^\ufeff/, '')
    .replace(/\s+/g, '');
}

function parseValue(
  key: keyof Customer,
  raw: string
): string | number | boolean | undefined {
  const value = raw.trim();
  if (value === '') return undefined;

  if (key === 'is_depot') {
    return ['1', 'true', 'yes', '是', '仓库'].includes(value.toLowerCase());
  }

  if (key === 'name') return value;

  const num = Number(value);
  return Number.isNaN(num) ? undefined : num;
}

function parseLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let insideQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (insideQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        insideQuotes = !insideQuotes;
      }
    } else if (char === ',' && !insideQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

export interface CsvParseResult {
  customers: Customer[];
  errors: string[];
}

export function parseCustomersCsv(text: string): CsvParseResult {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    return { customers: [], errors: ['CSV 文件至少需要包含表头和一行数据'] };
  }

  const headers = parseLine(lines[0]).map(normalizeHeader);
  const keys = headers
    .map((h) => HEADER_MAP[h])
    .map((key, index) => ({ key, index }));

  const missingRequired = ['id', 'name', 'lat', 'lon', 'demand'].filter(
    (field) => !keys.some((k) => k.key === field)
  );

  if (missingRequired.length > 0) {
    return {
      customers: [],
      errors: [`缺少必需字段: ${missingRequired.join(', ')}`],
    };
  }

  const customers: Customer[] = [];
  const errors: string[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = parseLine(lines[i]);
    const customer: Partial<Customer> = {};

    for (const { key, index } of keys) {
      if (!key || index >= values.length) continue;
      const parsed = parseValue(key, values[index]);
      if (parsed !== undefined) {
        (customer as Record<string, unknown>)[key] = parsed;
      }
    }

    if (
      typeof customer.id !== 'number' ||
      typeof customer.name !== 'string' ||
      typeof customer.lat !== 'number' ||
      typeof customer.lon !== 'number' ||
      typeof customer.demand !== 'number'
    ) {
      errors.push(`第 ${i + 1} 行数据格式不正确`);
      continue;
    }

    customers.push({
      id: customer.id,
      name: customer.name,
      lat: customer.lat,
      lon: customer.lon,
      demand: customer.demand,
      service_time_min: customer.service_time_min ?? 15,
      tw_earliest: customer.tw_earliest ?? 0,
      tw_latest: customer.tw_latest ?? 1440,
      is_depot: customer.is_depot ?? false,
    });
  }

  return { customers, errors };
}

export function customersToCsv(customers: Customer[]): string {
  const headers = [
    'id',
    'name',
    'lat',
    'lon',
    'demand',
    'service_time_min',
    'tw_earliest',
    'tw_latest',
    'is_depot',
  ];
  const rows = customers.map((c) =>
    [
      c.id,
      c.name,
      c.lat,
      c.lon,
      c.demand,
      c.service_time_min,
      c.tw_earliest,
      c.tw_latest,
      c.is_depot ? 'true' : 'false',
    ].join(',')
  );
  return [headers.join(','), ...rows].join('\n');
}
