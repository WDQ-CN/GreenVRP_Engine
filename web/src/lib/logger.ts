/**
 * 简单的环境感知日志工具。
 * - debug / info 仅在开发环境输出，避免生产构建保留调试日志。
 * - warn / error 始终输出，用于异常排查。
 */
export const logger = {
  debug: (...args: unknown[]) => {
    if (import.meta.env.DEV) {
      console.debug(...args);
    }
  },

  info: (...args: unknown[]) => {
    if (import.meta.env.DEV) {
      console.info(...args);
    }
  },

  warn: (...args: unknown[]) => {
    console.warn(...args);
  },

  error: (...args: unknown[]) => {
    console.error(...args);
  },
};
