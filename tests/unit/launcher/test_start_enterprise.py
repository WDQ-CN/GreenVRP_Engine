"""
单元测试：start_enterprise_ui.py — 企业前端启动器
"""

import os
import sys
import pytest


class TestEnterpriseLauncher:
    """start_enterprise_ui 启动逻辑测试。"""

    def test_module_importable(self):
        """模块应可正常导入。"""
        import start_enterprise_ui
        assert hasattr(start_enterprise_ui, "__name__")
