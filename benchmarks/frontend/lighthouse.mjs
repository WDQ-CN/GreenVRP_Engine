/**
 * 前端 Lighthouse 性能基准脚本
 *
 * 先构建前端产物，启动 vite preview，然后使用 Lighthouse 对首页进行评分，
 * 输出 Lighthouse Performance 评分、LCP 及 Web Vitals 到 JSON 文件。
 */

import { spawn } from 'child_process';
import fs from 'fs/promises';
import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '../..');
const webDir = path.join(projectRoot, 'web');
const resultsDir = path.join(__dirname, 'results');
const outputFile = path.join(resultsDir, 'lighthouse.json');
const port = 4173;
const targetUrl = `http://127.0.0.1:${port}`;

async function runCommand(cmd, args, options = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, {
      stdio: options.silent ? 'ignore' : 'inherit',
      shell: process.platform === 'win32',
      ...options,
    });
    let stdout = '';
    let stderr = '';
    if (options.capture) {
      proc.stdout.on('data', (d) => { stdout += d.toString(); });
      proc.stderr.on('data', (d) => { stderr += d.toString(); });
    }
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`${cmd} ${args.join(' ')} exited with ${code}\n${stderr}`));
      } else {
        resolve(stdout);
      }
    });
  });
}

async function waitForServer(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      // ignore
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`预览服务启动超时: ${url}`);
}

async function main() {
  let results = {
    url: targetUrl,
    error: null,
    scores: {},
    audits: {},
    timing: {},
  };

  try {
    // 从 web/node_modules 解析依赖（脚本位于 benchmarks/frontend，依赖安装于 web/）
    const require = createRequire(path.join(webDir, 'package.json'));
    const { default: lighthouse } = require('lighthouse');
    const chromeLauncher = require('chrome-launcher');

    // 构建
    console.log('构建前端产物...');
    await runCommand('npm', ['run', 'build'], { cwd: webDir });

    // 启动预览服务（直接调用 vite 二进制，避免 npm 包装层在 Windows 上参数拼接问题）
    console.log('启动 vite preview...');
    const viteBin = path.join(webDir, 'node_modules', 'vite', 'bin', 'vite.js');
    let previewExited = false;
    const preview = spawn(
      'node',
      [viteBin, 'preview', '--port', String(port), '--strictPort', '--host', '127.0.0.1'],
      {
        cwd: webDir,
        stdio: 'ignore',
        env: { ...process.env, BROWSER: 'none' },
      }
    );
    preview.on('exit', (code) => {
      previewExited = true;
      console.warn(`vite preview 已退出，code=${code}`);
    });

    try {
      await waitForServer(targetUrl);

      const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless', '--disable-gpu'] });
      try {
        const runnerResult = await lighthouse(targetUrl, {
          logLevel: 'error',
          output: 'json',
          onlyCategories: ['performance'],
          port: chrome.port,
        });

        const lhr = runnerResult.lhr;
        results.scores = {
          performance: lhr.categories.performance.score,
          accessibility: lhr.categories.accessibility?.score,
          bestPractices: lhr.categories['best-practices']?.score,
          seo: lhr.categories.seo?.score,
        };
        results.audits = {
          lcp: lhr.audits['largest-contentful-paint']?.numericValue,
          fcp: lhr.audits['first-contentful-paint']?.numericValue,
          tti: lhr.audits['interactive']?.numericValue,
          tbt: lhr.audits['total-blocking-time']?.numericValue,
          cls: lhr.audits['cumulative-layout-shift']?.numericValue,
          speedIndex: lhr.audits['speed-index']?.numericValue,
        };
        results.timing = lhr.timing;
      } finally {
        await chrome.kill();
      }
    } finally {
      preview.kill();
    }
  } catch (err) {
    results.error = err.message;
    console.error('Lighthouse 测试失败:', err.message);
  }

  await fs.mkdir(resultsDir, { recursive: true });
  await fs.writeFile(outputFile, JSON.stringify(results, null, 2), 'utf-8');
  console.log(`前端基准结果已保存: ${outputFile}`);
  console.log(JSON.stringify(results, null, 2));
}

main();
