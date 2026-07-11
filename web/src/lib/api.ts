import axios from 'axios';

import { toast } from '@/lib/toast';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
});

// 简单去重：最近 3 秒内相同消息只弹一次 toast，避免连续请求失败时刷屏
const recentToasts = new Set<string>();
const TOAST_DEDUPE_MS = 3000;

function showToast(title: string, description: string) {
  const key = `${title}|${description}`;
  if (recentToasts.has(key)) return;

  recentToasts.add(key);
  toast({ title, description, variant: 'destructive' });

  window.setTimeout(() => {
    recentToasts.delete(key);
  }, TOAST_DEDUPE_MS);
}

api.interceptors.request.use((config) => {
  const key = localStorage.getItem('greenvrp_api_key');
  if (key) {
    config.headers['X-API-Key'] = key;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }

    if (error.response) {
      const { status, data } = error.response;

      if (status === 401) {
        showToast('未授权', 'API Key 无效或未设置，请重新设置。');
        window.dispatchEvent(new CustomEvent('greenvrp:unauthorized'));
        return Promise.reject(new Error('未授权，请设置 API Key'));
      }

      if (status === 403) {
        showToast('禁止访问', '当前账号没有权限执行该操作。');
        return Promise.reject(new Error('禁止访问'));
      }

      if (status >= 500) {
        showToast('服务异常', '服务器暂时不可用，请稍后重试。');
        return Promise.reject(new Error('服务器暂时不可用，请稍后重试'));
      }

      const message = extractMessage(data) || '请求失败，请稍后重试';
      showToast('请求失败', message);
      return Promise.reject(new Error(message));
    }

    if (error.request) {
      showToast('网络错误', '无法连接到服务器，请检查网络或后端服务。');
      return Promise.reject(
        new Error('无法连接到服务器，请检查网络或后端服务')
      );
    }

    showToast('请求错误', '请求配置异常，请刷新页面重试。');
    return Promise.reject(new Error('请求配置异常'));
  }
);

function extractMessage(data: unknown): string | undefined {
  if (typeof data === 'string') {
    const trimmed = data.trim();
    if (trimmed.length === 0) return undefined;
    if (trimmed.startsWith('<')) return undefined;
    return trimmed;
  }
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>;
    if (typeof obj.detail === 'string') return obj.detail;
    if (typeof obj.message === 'string') return obj.message;
    if (Array.isArray(obj.detail) && obj.detail.length > 0) {
      return obj.detail
        .map((item) => (typeof item === 'string' ? item : JSON.stringify(item)))
        .join('；');
    }
  }
  return undefined;
}
