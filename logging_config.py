"""
日志配置模块

提供统一的日志配置与敏感数据脱敏功能。
"""

import logging
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 默认日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 敏感数据脱敏模式：(正则, 替换模板)
# 用于 SensitiveDataFilter 和 JsonFormatter
SENSITIVE_PATTERNS: List[Tuple[str, str]] = [
    # API Key: api_key = "xxx...yyy" 或 "api_key":"xxx...yyy"
    (r'(api_key["\']?\s*[:=]\s*["\']?)[^"\',;}\s]{8}([^"\',;}\s]{4,})', r'\1****\2'),
    # Bearer Token: 三段式 JWT (如 Bearer eyJxxx.yyy.zzz)
    (r'(Bearer\s+)([A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)+)', r'\1****'),
    # Password 字段
    (r'(password["\']?\s*[:=]\s*["\']?)([^"\',;}\s]+)', r'\1****'),
    # Secret 字段
    (r'(secret["\']?\s*[:=]\s*["\']?)([^"\',;}\s]+)', r'\1****'),
    # Token 字段（16位以上）
    (r'(token["\']?\s*[:=]\s*["\']?)([A-Za-z0-9_\-]{16,})', r'\1****'),
    # 疑似信用卡号（16位数字，可能含分隔符）
    (r'(\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4})', '****-****-****-****'),
    # Redis URL 密码（redis://user:pass@host:port）
    (r'(redis://[^:]+:)[^@]+(@)', r'\1****\2'),
]


class SensitiveDataFilter(logging.Filter):
    """日志敏感数据过滤器。

    在日志输出前对 API Key、Token、密码等敏感信息进行脱敏处理。
    使用正则模式匹配并替换为 **** 标记。

    可通过环境变量 ``GREENVRP_LOG_REDACT=false`` 禁用。
    """

    _compiled: List[Tuple[re.Pattern, str]] = []

    def __init__(self, name: str = ""):
        super().__init__(name)
        if not SensitiveDataFilter._compiled:
            SensitiveDataFilter._compiled = [
                (re.compile(pattern, re.IGNORECASE), replacement)
                for pattern, replacement in SENSITIVE_PATTERNS
            ]

    def filter(self, record: logging.LogRecord) -> bool:
        # 检查环境变量是否关闭脱敏
        import os
        if os.environ.get("GREENVRP_LOG_REDACT", "true").lower() == "false":
            return True

        # 脱敏 message
        if record.msg and isinstance(record.msg, str):
            for pattern, replacement in SensitiveDataFilter._compiled:
                record.msg = pattern.sub(replacement, record.msg)

        # 脱敏 args 中的字符串参数
        if record.args:
            sanitized = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in SensitiveDataFilter._compiled:
                        arg = pattern.sub(replacement, arg)
                sanitized.append(arg)
            record.args = tuple(sanitized)

        return True


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    module_levels: Optional[Dict[str, str]] = None,
) -> None:
    """
    配置应用程序日志。

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，None 表示不输出到文件
        log_format: 日志格式
        date_format: 日期格式
        module_levels: 模块级别的日志配置 {"module.name": "LEVEL"}
    """
    # 创建处理器
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        # 确保日志目录存在
        import os

        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    # 配置根日志
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )

    # 设置模块级别
    if module_levels:
        for module, module_level in module_levels.items():
            logging.getLogger(module).setLevel(getattr(logging, module_level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器。

    Args:
        name: 日志器名称

    Returns:
        Logger 实例
    """
    return logging.getLogger(name)


class ContextFilter(logging.Filter):
    """
    上下文过滤器，为日志记录添加额外信息。
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    """
    JSON 格式化器，将日志输出为 JSON 格式。
    输出前对敏感数据字段进行脱敏。
    """

    _compiled: List[Tuple[re.Pattern, str]] = []

    # 标准日志字段（不进行敏感数据扫描）
    STANDARD_FIELDS = {
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "msecs", "pathname",
        "process", "processName", "relativeCreated", "thread", "threadName",
        "exc_info", "exc_text", "stack_info", "message",
    }

    def __init__(self):
        super().__init__()
        if not JsonFormatter._compiled:
            JsonFormatter._compiled = [
                (re.compile(pattern, re.IGNORECASE), replacement)
                for pattern, replacement in SENSITIVE_PATTERNS
            ]

    def _redact(self, text: str) -> str:
        """对文本应用敏感数据脱敏。"""
        import os
        if os.environ.get("GREENVRP_LOG_REDACT", "true").lower() == "false":
            return text
        for pattern, replacement in self._compiled:
            text = pattern.sub(replacement, text)
        return text

    def format(self, record: logging.LogRecord) -> str:
        import json

        # 先应用 SensitiveDataFilter（如果存在）
        for f in record.logger.filters if hasattr(record, 'logger') else []:
            if isinstance(f, SensitiveDataFilter):
                f.filter(record)
                break

        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": self._redact(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self._redact(self.formatException(record.exc_info))

        # 添加额外字段（脱敏后）
        for key, value in record.__dict__.items():
            if key not in self.STANDARD_FIELDS:
                if isinstance(value, str):
                    log_data[key] = self._redact(value)
                else:
                    log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False)


def setup_json_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """
    配置 JSON 格式的日志输出。

    Args:
        level: 日志级别
        log_file: 日志文件路径
    """
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        import os

        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    # 设置 JSON 格式化器
    formatter = JsonFormatter()
    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
    )


# 预配置的日志器
solver_logger = get_logger("green_vrp.solver")
api_logger = get_logger("green_vrp.api")
tracking_logger = get_logger("green_vrp.tracking")
cost_logger = get_logger("green_vrp.cost")

# 为预配置日志器添加敏感数据脱敏过滤器
_sensitive_filter = SensitiveDataFilter()
for _logger in (solver_logger, api_logger, tracking_logger, cost_logger):
    # 避免重复添加
    if not any(isinstance(f, SensitiveDataFilter) for f in _logger.filters):
        _logger.addFilter(_sensitive_filter)
