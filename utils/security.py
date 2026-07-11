"""
前端安全工具函数。

用于 Streamlit 文件上传消毒、HTML 转义等。
"""

import html
from typing import Any

import pandas as pd
import streamlit as st

# CSV 上传安全限制
_MAX_CSV_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
_CSV_ALLOWED_ENCODINGS = ("utf-8", "utf-8-sig", "gbk", "gb2312")


def safe_read_csv(
    uploaded_file: Any,
    required_columns: list[str],
    max_size_bytes: int = _MAX_CSV_SIZE_BYTES,
) -> pd.DataFrame | None:
    """
    安全地读取用户上传的 CSV 文件。

    校验项：
    - 文件大小不超过 max_size_bytes
    - 仅解析 CSV，使用安全的编码列表
    - 必须包含 required_columns 指定的列

    返回解析后的 DataFrame；校验失败时通过 st.error 提示并返回 None。
    """
    if uploaded_file is None:
        return None

    # 文件大小校验
    uploaded_file.seek(0, 2)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    if size > max_size_bytes:
        st.error(f"文件过大，请上传小于 {max_size_bytes / 1024 / 1024:.1f} MB 的 CSV")
        return None

    # 尝试安全编码读取
    df: pd.DataFrame | None = None
    last_error: Exception | None = None
    for encoding in _CSV_ALLOWED_ENCODINGS:
        try:
            df = pd.read_csv(uploaded_file, encoding=encoding)
            break
        except Exception as exc:  # noqa: BLE001
            uploaded_file.seek(0)
            last_error = exc
    else:
        st.error(f"无法解析 CSV 文件，请使用 UTF-8 或 GBK 编码: {last_error}")
        return None

    # 列名校验
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"缺少列: {missing}")
        return None

    return df


def escape_html(text: str) -> str:
    """转义 HTML 特殊字符，防止 XSS。"""
    return html.escape(str(text))
