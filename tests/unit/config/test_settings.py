"""
单元测试：config/settings.py — Settings 配置管理
"""

import os
from unittest.mock import patch

import pytest

from config.settings import Settings, get_settings, set_settings


class TestSettings:
    def test_default_values(self):
        settings = Settings()
        assert settings.app_name == "GreenVRP Engine"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.default_time_limit_seconds == 60
        assert settings.max_time_limit_seconds == 300
        assert settings.log_level == "INFO"

    def test_from_env_defaults(self):
        settings = Settings.from_env()
        assert settings.debug is False
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000

    def test_from_env_with_env_vars(self):
        with patch.dict(os.environ, {
            "GREENVRP_DEBUG": "true",
            "GREENVRP_API_HOST": "127.0.0.1",
            "GREENVRP_API_PORT": "9000",
            "GREENVRP_LOG_LEVEL": "DEBUG",
        }, clear=False):
            settings = Settings.from_env()
            assert settings.debug is True
            assert settings.api_host == "127.0.0.1"
            assert settings.api_port == 9000
            assert settings.log_level == "DEBUG"

    def test_from_env_with_log_file(self):
        with patch.dict(os.environ, {"GREENVRP_LOG_FILE": "/tmp/test.log"}, clear=False):
            settings = Settings.from_env()
            assert settings.log_file == "/tmp/test.log"

    def test_get_settings_singleton(self):
        set_settings(Settings(debug=True))
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
        assert s1.debug is True

    def test_set_settings(self):
        s = Settings(api_port=8080)
        set_settings(s)
        assert get_settings().api_port == 8080
