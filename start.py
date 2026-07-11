# ruff: noqa: T201
"""
GreenVRP Engine 统一启动器 v3 - 性能优化版

提供多种启动方式：
1. Web 界面 (Streamlit)
2. API 服务 (FastAPI + Uvicorn)
3. 命令行求解

使用方法：
    python start.py              # 交互式选择
    python start.py web          # 启动 Web 界面
    python start.py api          # 启动 API 服务
    python start.py api --port 8001  # 指定端口
    python start.py solve --input data.csv --output result.json

性能优化 v3：
- 延迟导入：按需导入重型库
- 并行导入：使用线程加速模块加载
- 缓存预编译：加速Python字节码加载
- 启动时序分析：识别和优化慢路径
"""

# ========== 启动速度优化：阶段0 - 最快速的基础设置 ==========
import os
import sys

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目路径（确保能快速找到模块）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 延迟导入重型库 - 只在需要时导入
_import_cache = {}


def _lazy_import(module_name: str):
    """延迟导入模块，缓存结果。"""
    if module_name not in _import_cache:
        _import_cache[module_name] = __import__(module_name)
    return _import_cache[module_name]


# 启动时序分析（如需要，通过环境变量启用）
START_TIME = None
if os.environ.get("GREENVRP_PROFILE_STARTUP"):
    import time

    START_TIME = time.perf_counter()
    _timing_points = [("start", 0.0)]

    def _log_timing(label: str):
        elapsed = time.perf_counter() - START_TIME
        _timing_points.append((label, elapsed))
else:

    def _log_timing(label: str):
        pass


# 在阶段1中导入argparse
import argparse  # noqa: E402
import subprocess  # noqa: E402


def start_web():
    """启动 Streamlit Web 界面。"""

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
    """启动 FastAPI 服务。"""

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
    """命令行求解。"""
    import json
    import time

    import pandas as pd

    from config.constants import DEFAULT_PARAMS
    from config.vehicles import DEFAULT_VEHICLE_CONFIG
    from core.cost import calculate_green_cost
    from core.solver import solve_with_multiple_strategies

    # 加载数据
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"错误：输入文件不存在: {input_file}")
        return
    except Exception as e:
        print(f"错误：无法读取输入文件: {e}")
        return

    # 求解
    start = time.time()
    solution = solve_with_multiple_strategies(
        customers_df=df,
        vehicle_config=DEFAULT_VEHICLE_CONFIG,
        time_limit=time_limit,
    )
    elapsed = time.time() - start

    # 计算成本
    cost_result = calculate_green_cost(solution, DEFAULT_VEHICLE_CONFIG, DEFAULT_PARAMS)

    # 保存结果
    if output_file:
        result = {
            "solution": solution,
            "cost_result": cost_result,
            "solve_time": elapsed,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"结果已保存: {output_file}")
    else:
        print(json.dumps(cost_result, ensure_ascii=False, indent=2, default=str))


def interactive_mode():
    """交互式选择启动模式。"""
    _log_timing("interactive_mode_start")

    print("\nGreenVRP Engine 启动器")
    print("1. 启动 Web 界面 (Streamlit)")
    print("2. 启动 API 服务 (FastAPI + Uvicorn)")
    print("3. 命令行求解")
    choice = input("  请输入选项 (1-3): ").strip()

    if choice == "1":
        start_web()
    elif choice == "2":
        port = input("  请输入端口号 (默认 8000): ").strip()
        port = int(port) if port.isdigit() else 8000
        start_api(port=port)
    elif choice == "3":
        input_file = input("  请输入输入文件路径: ").strip()
        output_file = input("  请输入输出文件路径 (可选): ").strip() or None
        time_limit = input("  请输入求解时间限制秒数 (默认 60): ").strip()
        time_limit = int(time_limit) if time_limit.isdigit() else 60
        solve_cli(input_file, output_file, time_limit)
    else:
        print("无效选项，请重新运行并选择 1-3。")

    _log_timing("interactive_mode_end")


def main():
    parser = argparse.ArgumentParser(
        description="GreenVRP Engine 启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start.py                    # 交互式选择
  python start.py web                # 启动 Web 界面
  python start.py api                # 启动 API 服务
  python start.py api --port 8001    # 指定端口
  python start.py solve -i data.csv -o result.json
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

    args = parser.parse_args()

    if args.mode == "web":
        start_web()
    elif args.mode == "api":
        start_api(port=args.port, reload=not args.no_reload)
    elif args.mode == "solve":
        solve_cli(args.input, args.output, args.time_limit)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
