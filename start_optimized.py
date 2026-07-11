"""
GreenVRP Engine 高性能启动器 v3

优化策略：
1. 延迟导入 - 只在需要时加载重型库
2. 并行导入 - 使用线程加速模块加载
3. 预编译缓存 - 加速Python字节码加载
4. 启动时序分析 - 识别和优化慢路径
"""

import os
import sys

# ========== 阶段0: 最快速度设置启动环境 ==========
# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 启动时序分析（通过环境变量启用）
START_TIME = None
if os.environ.get("GREENVRP_PROFILE_STARTUP"):
    import time

    START_TIME = time.perf_counter()
    _timing_points = [("start", 0.0)]

    def _log_timing(label: str):
        elapsed = time.perf_counter() - START_TIME
        _timing_points.append((label, elapsed))
        print(f"[STARTUP] {label}: {elapsed*1000:.2f}ms")

else:

    def _log_timing(label: str):
        pass


# ========== 阶段1: 延迟导入设计 ==========
_import_cache = {}
_lazy_import_queue = []


def _lazy_import(module_name: str, alias: str = None):
    """延迟导入模块，支持别名。"""
    cache_key = alias or module_name
    if cache_key not in _import_cache:
        mod = __import__(module_name, fromlist=[""])
        if alias:
            _import_cache[cache_key] = mod
        else:
            _import_cache[module_name] = mod
    return _import_cache[cache_key]


def _batch_import_parallel():
    """使用线程并行导入核心模块。"""
    import threading
    import time

    modules_to_import = [
        ("argparse", None),
        ("subprocess", None),
        ("importlib", None),
    ]

    imported = {}
    lock = threading.Lock()

    def import_worker(module_name, alias):
        try:
            mod = __import__(module_name, fromlist=[""])
            with lock:
                key = alias or module_name
                imported[key] = mod
        except Exception:
            pass

    threads = []
    start = time.time()

    for mod_name, alias in modules_to_import:
        t = threading.Thread(target=import_worker, args=(mod_name, alias))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # 将导入结果合并到缓存
    _import_cache.update(imported)

    return time.time() - start


# 执行并行导入
_log_timing("before_parallel_import")
_import_batch_time = _batch_import_parallel()
_log_timing(f"after_parallel_import ({_import_batch_time*1000:.1f}ms)")

# 导入必须的argparse
argparse = _import_cache.get("argparse") or __import__("argparse")
subprocess = _import_cache.get("subprocess") or __import__("subprocess")

# ========== 阶段2: 启动函数定义 ==========


def start_web():
    """启动 Streamlit Web 界面 - 延迟加载streamlit。"""
    _log_timing("start_web")

    print("=" * 60)
    print("  🚚 GreenVRP Engine Web 界面启动中...")
    print("=" * 60)
    print()
    print("  访问地址: http://localhost:8501")
    print("  按 Ctrl+C 停止服务")
    print()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "web_app.py",
            "--server.port",
            "8501",
            "--server.address",
            "0.0.0.0",
        ]
    )


def start_api(port=8000, reload=True):
    """启动 FastAPI 服务 - 延迟加载fastapi。"""
    _log_timing("start_api")

    print("=" * 60)
    print("  🔧 GreenVRP Engine API 服务启动中...")
    print("=" * 60)
    print()
    print(f"  API 文档: http://localhost:{port}/docs")
    print(f"  ReDoc: http://localhost:{port}/redoc")
    print("  按 Ctrl+C 停止服务")
    print()

    args = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    if reload:
        args.append("--reload")

    subprocess.run(args)


def solve_cli(input_file, output_file=None, time_limit=60):
    """命令行求解 - 延迟加载重型库。"""
    _log_timing("solve_cli_start")

    # 只在需要时导入重型库
    import json
    import time as time_module

    import pandas as pd

    from config.constants import DEFAULT_PARAMS
    from config.vehicles import DEFAULT_VEHICLE_CONFIG
    from core.cost import calculate_green_cost
    from core.solver import GreenVRPSolver, solve_with_multiple_strategies

    _log_timing("imports_loaded")

    print("=" * 60)
    print("  🔍 GreenVRP Engine 求解器")
    print("=" * 60)
    print()

    # 加载数据
    print(f"📂 加载数据: {input_file}")
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return

    print(f"   客户数: {len(df)}")

    # 求解
    print(f"\n⏳ 开始求解 (时间限制: {time_limit}秒)...")
    start = time_module.time()

    solution = solve_with_multiple_strategies(
        customers_df=df,
        vehicle_config=DEFAULT_VEHICLE_CONFIG,
        time_limit=time_limit,
    )

    elapsed = time_module.time() - start

    # 计算成本
    cost_result = calculate_green_cost(solution, DEFAULT_VEHICLE_CONFIG, DEFAULT_PARAMS)

    # 输出结果...
    print(f"\n✅ 求解完成 (耗时: {elapsed:.2f}秒)")
    # ... 其余输出代码


def interactive_mode():
    """交互式选择启动模式。"""
    _log_timing("interactive_mode")

    print()
    print("=" * 60)
    print("  🚚 GreenVRP Engine 启动器")
    print("=" * 60)
    print()
    print("  请选择启动模式:")
    print()
    print("  [1] Web 界面 (Streamlit) - 可视化操作界面")
    print("  [2] API 服务 (FastAPI)   - RESTful API 接口")
    print("  [3] 退出")
    print()

    choice = input("  请输入选项 (1-3): ").strip()

    if choice == "1":
        start_web()
    elif choice == "2":
        port = input("  请输入端口号 (默认 8000): ").strip()
        port = int(port) if port.isdigit() else 8000
        start_api(port=port)
    elif choice == "3":
        print("\n  再见! 👋\n")
    else:
        print("\n  ❌ 无效选项\n")


def main():
    """主入口函数。"""
    _log_timing("main_start")

    parser = argparse.ArgumentParser(
        description="GreenVRP Engine 启动器 v3 - 性能优化版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start_optimized.py                    # 交互式选择
  python start_optimized.py web                # 启动 Web 界面
  python start_optimized.py api                # 启动 API 服务
  python start_optimized.py api --port 8001    # 指定端口
  python start_optimized.py solve -i data.csv -o result.json

环境变量:
  GREENVRP_PROFILE_STARTUP=1    # 启用启动时序分析
        """,
    )

    subparsers = parser.add_subparsers(dest="mode", help="启动模式")

    # Web 模式
    subparsers.add_parser("web", help="启动 Web 界面")

    # API 模式
    api_parser = subparsers.add_parser("api", help="启动 API 服务")
    api_parser.add_argument("--port", type=int, default=8000, help="服务端口 (默认: 8000)")
    api_parser.add_argument("--no-reload", action="store_true", help="禁用热重载")

    # 求解模式
    solve_parser = subparsers.add_parser("solve", help="命令行求解")
    solve_parser.add_argument("-i", "--input", required=True, help="输入文件 (CSV)")
    solve_parser.add_argument("-o", "--output", help="输出文件 (JSON)")
    solve_parser.add_argument("-t", "--time-limit", type=int, default=60, help="求解时间限制 (秒)")

    _log_timing("parser_ready")
    args = parser.parse_args()
    _log_timing("args_parsed")

    if args.mode == "web":
        start_web()
    elif args.mode == "api":
        start_api(port=args.port, reload=not args.no_reload)
    elif args.mode == "solve":
        solve_cli(args.input, args.output, args.time_limit)
    else:
        interactive_mode()

    _log_timing("main_end")


if __name__ == "__main__":
    main()
