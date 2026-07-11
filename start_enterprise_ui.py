"""
企业简约风格前端启动脚本
"""

import sys

if __name__ == "__main__":
    import os

    # 确保在正确的目录中运行
    frontend_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_path = os.path.join(frontend_dir, "frontend", "app_enhanced.py")

    if not os.path.exists(frontend_path):
        sys.exit(1)

    # 使用 Streamlit 运行前端应用
    import streamlit.cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        frontend_path,
        "--theme.base",
        "light",
        "--theme.primaryColor",
        "#2C3E50",
        "--theme.secondaryBackgroundColor",
        "#ECF0F1",
        "--theme.backgroundColor",
        "#FFFFFF",
        "--theme.textColor",
        "#2C3E50",
    ]

    stcli.main()
