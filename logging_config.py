"""
日志配置模块

提供统一的日志配置功能。
"""

import logging
import sys
from datetime import datetime
from typing import Any

# 默认日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    module_levels: dict[str, str] | None = None,
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

    def __init__(self, context: dict[str, Any] | None = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    """
    JSON 格式化器，将日志输出为 JSON 格式。
    """

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "message",
                "timestamp",
                "logger",
                "level",
            ]:
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False)


def setup_json_logging(
    level: str = "INFO",
    log_file: str | None = None,
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
