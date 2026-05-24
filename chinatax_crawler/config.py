"""
全局配置模块。

可通过环境变量 ``CHINATAX_*`` 覆盖默认值，
优先级：CLI参数 > 环境变量 > config.py默认值。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# ─── 默认路径 ───────────────────────────────────────────────
PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent
DATA_DIR: Final = PROJECT_ROOT / "data"
CHECKPOINT_DIR: Final = DATA_DIR / "checkpoint"


@dataclass
class Config:
    """爬虫全局配置。"""

    # ── 目标网站 ──
    base_url: str = "https://www.chinatax.gov.cn"
    list_url_template: str = (
        "https://www.chinatax.gov.cn/chinatax/manuscriptList/c102025"
        "?_isAgg=0&_pageSize=20&_template=index"
        "&_channelName=税案通报&_keyWH=wenhao&page={page}"
    )
    total_pages: int = 55
    items_per_page: int = 20

    # ── 请求控制 ──
    request_delay: float = 1.0         # 请求间隔（秒）
    request_timeout: int = 30          # 单次请求超时（秒）
    max_retries: int = 3               # 最大重试次数
    retry_backoff: float = 2.0         # 重试退避乘数

    # ── User-Agent ──
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # ── 输出 ──
    data_dir: Path = DATA_DIR
    output_format: str = "json"        # json | jsonl | csv
    output_name: str = "chinatax_cases"  # 不含扩展名

    # ── 爬取模式 ──
    list_only: bool = False            # 仅抓取列表
    full_text: bool = True             # 是否抓取文章正文
    resume: bool = True                # 断点续传
    max_articles: int = 0              # 最多抓取文章数（0=不限）

    # ── 日志 ──
    log_level: str = "INFO"
    log_file: Path | None = None

    # ── 检查点 ──
    checkpoint_dir: Path = CHECKPOINT_DIR
    checkpoint_interval: int = 50      # 每N篇文章保存一次检查点

    def __post_init__(self) -> None:
        """从环境变量覆盖配置。"""
        # 确保路径字段始终是 Path 对象
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        if isinstance(self.checkpoint_dir, str):
            self.checkpoint_dir = Path(self.checkpoint_dir)
        if isinstance(self.log_file, str):
            self.log_file = Path(self.log_file)

        for key in self.__dataclass_fields__:
            env_key = f"CHINATAX_{key.upper()}"
            env_val = os.environ.get(env_key)
            if env_val is not None:
                self._apply_env(key, env_val)

        # 确保路径类型正确
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        if isinstance(self.checkpoint_dir, str):
            self.checkpoint_dir = Path(self.checkpoint_dir)

        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _apply_env(self, key: str, raw: str) -> None:
        """将环境变量值转换为正确的类型并设置。"""
        field_type = self.__dataclass_fields__[key].type
        current = getattr(self, key)

        try:
            if isinstance(current, bool):
                setattr(self, key, raw.lower() in ("1", "true", "yes"))
            elif isinstance(current, int):
                setattr(self, key, int(raw))
            elif isinstance(current, float):
                setattr(self, key, float(raw))
            elif isinstance(current, Path):
                setattr(self, key, Path(raw))
            else:
                setattr(self, key, raw)
        except (ValueError, TypeError):
            pass  # 保持默认值


# 全局单例
config = Config()
