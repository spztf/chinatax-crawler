"""
工具函数模块：日志、重试、HTTP会话管理。
"""

from __future__ import annotations

import logging
import time
import functools
from typing import Any, Callable, TypeVar

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import config

F = TypeVar("F", bound=Callable[..., Any])

# ─── 日志 ──────────────────────────────────────────────────


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    name: str = "chinatax_crawler",
) -> logging.Logger:
    """配置并返回应用日志器。"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_file:
        from pathlib import Path
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


logger = setup_logging(config.log_level,
                       str(config.log_file) if config.log_file else None)


# ─── HTTP 会话 ──────────────────────────────────────────────


def create_session() -> requests.Session:
    """创建带重试策略的 requests Session。"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": config.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })

    # urllib3 重试策略
    retry_strategy = Retry(
        total=config.max_retries,
        backoff_factor=config.retry_backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


# ─── 装饰器工具 ────────────────────────────────────────────


def retry_on_failure(
    max_tries: int | None = None,
    delay: float | None = None,
    backoff: float | None = None,
) -> Callable[[F], F]:
    """请求失败时指数退避重试的装饰器。

    Parameters
    ----------
    max_tries : int
        最大尝试次数（含首次）。
    delay : float
        初始等待秒数。
    backoff : float
        每次退避乘数。
    """
    _tries = max_tries or config.max_retries + 1
    _delay = delay or config.request_delay
    _backoff = backoff or config.retry_backoff

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc = None
            wait = _delay
            for attempt in range(1, _tries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, IOError) as exc:
                    last_exc = exc
                    if attempt < _tries:
                        logger.warning(
                            "请求失败 (第 %d/%d 次): %s，%0.1fs 后重试...",
                            attempt, _tries, exc, wait)
                        time.sleep(wait)
                        wait *= _backoff
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator


def rate_limit(min_interval: float | None = None) -> Callable[[F], F]:
    """简单的请求频率限制装饰器。"""
    _interval = min_interval or config.request_delay
    last_call: dict[str, float] = {"ts": 0.0}

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            elapsed = time.monotonic() - last_call["ts"]
            if elapsed < _interval:
                time.sleep(_interval - elapsed)
            result = func(*args, **kwargs)
            last_call["ts"] = time.monotonic()
            return result
        return wrapper  # type: ignore[return-value]
    return decorator


# ─── 其他工具 ──────────────────────────────────────────────


def safe_filename(text: str, max_len: int = 80) -> str:
    """将文本转换为安全的文件名。"""
    import re
    safe = re.sub(r'[\\/*?:"<>|]', '_', text)
    safe = re.sub(r'\s+', '_', safe)
    return safe[:max_len].rstrip('_')
