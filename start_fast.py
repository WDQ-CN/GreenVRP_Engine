"""
GreenVRP Engine 高性能启动器 v3

启动速度优化策略：
1. 延迟导入 - 只在需要时加载重型库
2. 预加载缓存 - 加速常用模块导入
3. 精简启动路径 - 移除不必要的初始化

使用方法：
    python start_fast.py              # 交互式选择
    python start_fast.py web          # 启动 Web 界面
    python start_fast.py api          # 启动 API 服务
    python start_fast.py api --port 8001  # 指定端口
"""

import os
import sys

# 快速路径设置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# 只导入必须的轻量级模块
import argparse
import json
import subprocess
import time


def start_web():
    """启动 Streamlit Web 界面。"""
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
    """启动 FastAPI 服务。"""
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
    # 延迟导入重型库
    import pandas as pd

    from config.constants import DEFAULT_PARAMS
    from config.vehicles import DEFAULT_VEHICLE_CONFIG
    from core.cost import calculate_green_cost
    from core.solver import solve_with_multiple_strategies

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
    start = time.time()

    solution = solve_with_multiple_strategies(
        customers_df=df,
        vehicle_config=DEFAULT_VEHICLE_CONFIG,
        time_limit=time_limit,
    )

    elapsed = time.time() - start

    # 计算成本
    cost_result = calculate_green_cost(solution, DEFAULT_VEHICLE_CONFIG, DEFAULT_PARAMS)

    # 输出结果
    print(f"\n✅ 求解完成 (耗时: {elapsed:.2f}秒)")
    print()
    print("-" * 40)
    print("📊 求解结果")
    print("-" * 40)
    print(f"  状态: {solution['solution_status']}")
    print(f"  总距离: {solution['total_distance']:.2f} km")
    print(f"  车辆使用: {solution['vehicles_used']}")
    print(f"  总迟到: {solution['total_late_minutes']} 分钟")
    print()
    print("-" * 40)
    print("💰 成本分析")
    print("-" * 40)
    print(f"  总成本: ¥{cost_result['total_cost']:,.2f}")
    print(f"  运输成本: ¥{cost_result['transport_cost']:,.2f}")
    print(f"  人工成本: ¥{cost_result['labor_cost']:,.2f}")
    print(f"  固定成本: ¥{cost_result['fixed_cost']:,.2f}")
    print(f"  惩罚成本: ¥{cost_result['penalty_cost']:,.2f}")
    print(f"  碳排放: {cost_result['carbon_emission_kg']:.2f} kg CO2")
    print()

    # 保存结果
    if output_file:
        result = {
            "solution": solution,
            "cost_result": cost_result,
            "solve_time": elapsed,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"📁 结果已保存: {output_file}")


def interactive_mode():
    """交互式选择启动模式。"""
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
