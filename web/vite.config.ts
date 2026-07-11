import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 仅在 ANALYZE=true 时加载打包分析插件，避免影响常规构建
const visualizer = process.env.ANALYZE
  ? (await import('rollup-plugin-visualizer')).visualizer
  : undefined;

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    visualizer
      ? visualizer({
          open: true,
          gzipSize: true,
          brotliSize: true,
          filename: 'dist/stats.html',
        })
      : undefined,
  ].filter(Boolean),
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    target: 'es2022',
    modulePreload: {
      // 现代浏览器已原生支持 modulepreload，关闭 polyfill 减少入口体积
      polyfill: false,
      // 图表库仅在分析页面懒加载，避免在首屏预加载 400KB+ 的 vendor-charts
      resolveDependencies: (_filename, deps) =>
        deps.filter((dep) => !/vendor-charts/.test(dep)),
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (
              id.includes('react') ||
              id.includes('react-dom') ||
              id.includes('react-router-dom')
            ) {
              return 'vendor-react';
            }

            if (
              id.includes('axios') ||
              id.includes('zustand') ||
              id.includes('@tanstack/react-query')
            ) {
              return 'vendor-state';
            }

            if (
              id.includes('@radix-ui') ||
              id.includes('lucide-react') ||
              id.includes('class-variance-authority') ||
              id.includes('tailwind-merge') ||
              id.includes('clsx')
            ) {
              return 'vendor-ui';
            }

            if (id.includes('recharts')) {
              return 'vendor-charts';
            }

            // 其他第三方依赖
            return 'vendor-other';
          }
          return undefined;
        },
      },
    },
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // 生成 source map 方便调试（生产环境可设为 false）
    sourcemap: false,
  },
});
