"""
单元测试：logging_config.py — 日志配置与敏感数据脱敏
"""

import logging
import json
import logging
import re
import sys

import pytest


class TestSensitiveDataFilter:
    """SensitiveDataFilter 脱敏效果测试。"""

    @pytest.fixture(autouse=True)
    def _import_filter(self):
        from logging_config import SensitiveDataFilter
        self.filter = SensitiveDataFilter()

    def _make_record(self, msg: str, level=logging.INFO) -> logging.LogRecord:
        return logging.LogRecord("test", level, "", 0, msg, None, None)

    def test_redact_api_key_json(self):
        """API Key 在 JSON 格式中被脱敏。"""
        record = self._make_record(
            '{"api_key": "sk-1234567890abcdef"}'
        )
        self.filter.filter(record)
        assert "****" in record.msg
        assert "sk-1234567890" not in record.msg

    def test_redact_api_key_assignment(self):
        """API Key 在赋值语句中被脱敏。"""
        record = self._make_record(
            'api_key = "sk-1234567890abcdef"'
        )
        self.filter.filter(record)
        assert "****" in record.msg
        assert "sk-1234567890" not in record.msg

    def test_redact_bearer_token(self):
        """JWT Bearer Token（三段式）被完整脱敏。"""
        record = self._make_record(
            'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.test123'
        )
        self.filter.filter(record)
        assert "****" in record.msg
        # 不应出现完整的三段式 token
        assert "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0" not in record.msg

    def test_redact_password_field(self):
        """Password 字段被脱敏。"""
        record = self._make_record(
            'password = "super-secret-123"'
        )
        self.filter.filter(record)
        assert "****" in record.msg
        assert "super-secret-123" not in record.msg

    def test_redact_secret_field(self):
        """Secret 字段被脱敏。"""
        record = self._make_record(
            'secret = "my-api-secret-value"'
        )
        self.filter.filter(record)
        assert "****" in record.msg
        assert "my-api-secret-value" not in record.msg

    def test_redact_token_field(self):
        """Token 字段（16位以上）被脱敏。"""
        record = self._make_record(
            'token = "ghp_abcdefghijklmnopqrstuvwxyz123456"'
        )
        self.filter.filter(record)
        assert "****" in record.msg
        assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in record.msg

    def test_normal_message_not_affected(self):
        """正常日志消息不应被破坏。"""
        msg = "Route optimization completed: 5 vehicles, 120.5 km"
        record = self._make_record(msg)
        self.filter.filter(record)
        assert record.msg == msg

    def test_empty_message_not_crash(self):
        """空消息不应崩溃。"""
        record = self._make_record("")
        self.filter.filter(record)
        assert record.msg == ""

    def test_non_string_message_not_crash(self):
        """非字符串消息不应崩溃。"""
        record = logging.LogRecord("test", logging.ERROR, "", 0, "Error: %s", (42,), None)
        self.filter.filter(record)
        # 不应抛异常

    def test_multi_line_sensitive_data(self):
        """多行日志中的敏感数据也被脱敏。"""
        record = self._make_record(
            "Line 1: api_key = sk-1234567890abcdef\n"
            "Line 2: password = secret123"
        )
        self.filter.filter(record)
        assert "sk-1234567890" not in record.msg
        assert "secret123" not in record.msg
        assert "****" in record.msg


class TestJsonFormatter:
    """JsonFormatter 格式与脱敏测试。"""

    @pytest.fixture(autouse=True)
    def _import_formatter(self):
        from logging_config import JsonFormatter, SensitiveDataFilter
        self.formatter = JsonFormatter()
        self.filter = SensitiveDataFilter()

    def _make_and_format(self, msg: str, level=logging.INFO) -> str:
        record = logging.LogRecord("test", level, "", 0, msg, None, None)
        # 先过滤再格式化
        self.filter.filter(record)
        return self.formatter.format(record)

    def test_json_output_structure(self):
        """JSON 输出应包含标准字段。"""
        output = self._make_and_format("test message")
        data = json.loads(output)
        assert "timestamp" in data
        assert "logger" in data
        assert "level" in data
        assert "message" in data
        assert data["message"] == "test message"

    def test_json_api_key_redacted(self):
        """JSON 输出中 API Key 应被脱敏。"""
        output = self._make_and_format('api_key = "sk-1234567890abcdef"')
        data = json.loads(output)
        assert "sk-1234567890" not in data["message"]
        assert "****" in data["message"]

    def test_json_bearer_token_redacted(self):
        """JSON 输出中 Bearer Token 应被脱敏。"""
        output = self._make_and_format(
            'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.test123'
        )
        data = json.loads(output)
        assert "eyJhbGciOiJIUzI1NiJ9" not in data["message"]
        assert "****" in data["message"]

    def test_json_with_exception(self):
        """包含异常信息的 JSON 日志。"""
        try:
            raise ValueError("test error")
        except ValueError:
            record = logging.LogRecord(
                "test", logging.ERROR, "", 0, "An error occurred", None, None
            )
            record.exc_info = sys.exc_info()
            self.filter.filter(record)
            output = self.formatter.format(record)
            data = json.loads(output)
            assert "exception" in data
            assert "ValueError" in data["exception"]


class TestPreconfiguredLoggers:
    """预配置日志器应包含 SensitiveDataFilter。"""

    def test_solver_logger_has_filter(self):
        from logging_config import solver_logger, SensitiveDataFilter
        has_filter = any(isinstance(f, SensitiveDataFilter) for f in solver_logger.filters)
        assert has_filter, "solver_logger 缺少 SensitiveDataFilter"

    def test_api_logger_has_filter(self):
        from logging_config import api_logger, SensitiveDataFilter
        has_filter = any(isinstance(f, SensitiveDataFilter) for f in api_logger.filters)
        assert has_filter, "api_logger 缺少 SensitiveDataFilter"

    def test_tracking_logger_has_filter(self):
        from logging_config import tracking_logger, SensitiveDataFilter
        has_filter = any(isinstance(f, SensitiveDataFilter) for f in tracking_logger.filters)
        assert has_filter, "tracking_logger 缺少 SensitiveDataFilter"

    def test_cost_logger_has_filter(self):
        from logging_config import cost_logger, SensitiveDataFilter
        has_filter = any(isinstance(f, SensitiveDataFilter) for f in cost_logger.filters)
        assert has_filter, "cost_logger 缺少 SensitiveDataFilter"
