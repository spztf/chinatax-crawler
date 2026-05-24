"""
数据存储模块。

支持 JSON、JSONL、CSV 三种输出格式，
以及断点续传所需的检查点文件。
"""

from __future__ import annotations

import csv
import json
import pickle
from pathlib import Path
from typing import Any

from .config import config
from .parser import ArticleItem, ListItem
from .utils import logger


class Storage:
    """管理爬取结果的持久化存储。

    Parameters
    ----------
    data_dir : Path
        数据输出目录。
    output_name : str
        输出文件名（不含扩展名）。
    """

    def __init__(
        self,
        data_dir: Path | str | None = None,
        output_name: str | None = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else config.data_dir
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        self.output_name = output_name or config.output_name
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ── JSON 输出 ──────────────────────────────────────────

    def save_json(self, articles: list[ArticleItem]) -> Path:
        """保存为格式化的 JSON 文件。"""
        path = self.data_dir / f"{self.output_name}.json"
        data = [a.to_dict() for a in articles]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("已保存 %d 条记录到 %s", len(articles), path)
        return path

    # ── JSONL 输出 ─────────────────────────────────────────

    def save_jsonl(self, articles: list[ArticleItem]) -> Path:
        """保存为 JSONL 文件（每行一条JSON）。"""
        path = self.data_dir / f"{self.output_name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for a in articles:
                f.write(json.dumps(a.to_dict(), ensure_ascii=False) + "\n")
        logger.info("已保存 %d 条记录到 %s", len(articles), path)
        return path

    def append_jsonl(self, article: ArticleItem, path: Path | None = None) -> Path:
        """追加单条记录到 JSONL 文件（用于增量写入）。"""
        if path is None:
            path = self.data_dir / f"{self.output_name}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(article.to_dict(), ensure_ascii=False) + "\n")
        return path

    # ── CSV 输出 ───────────────────────────────────────────

    def save_csv(
        self,
        articles: list[ArticleItem] | list[ListItem],
    ) -> Path:
        """保存为 CSV 文件。"""
        path = self.data_dir / f"{self.output_name}.csv"

        if not articles:
            return path

        first = articles[0]
        if isinstance(first, ArticleItem):
            fieldnames = [
                "article_id", "title", "url", "publish_date",
                "source", "editor", "content_text",
            ]
            rows = [
                {k: a.to_dict().get(k, "") for k in fieldnames}
                for a in articles
            ]
        else:
            fieldnames = ["article_id", "title", "url", "publish_date"]
            rows = [a.__dict__ for a in articles]

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("已保存 %d 条记录到 %s", len(articles), path)
        return path

    # ── 列表索引保存 ───────────────────────────────────────

    def save_index(self, items: list[ListItem]) -> Path:
        """保存文章索引（不含正文）为 JSON。"""
        path = self.data_dir / f"{self.output_name}_index.json"
        data: list[dict[str, Any]] = [
            {
                "article_id": i.article_id,
                "title": i.title,
                "url": i.url,
                "publish_date": i.publish_date,
            }
            for i in items
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("索引已保存: %d 条 → %s", len(items), path)
        return path

    def load_index(self) -> list[ListItem]:
        """加载已保存的索引文件。"""
        path = self.data_dir / f"{self.output_name}_index.json"
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            ListItem(
                article_id=d.get("article_id", ""),
                title=d.get("title", ""),
                url=d.get("url", ""),
                publish_date=d.get("publish_date", ""),
            )
            for d in data
        ]

    # ── 检查点（断点续传） ─────────────────────────────────

    def _checkpoint_path(self) -> Path:
        return config.checkpoint_dir / f"{self.output_name}_checkpoint.pkl"

    def save_checkpoint(self, completed_ids: set[str]) -> None:
        """保存检查点（已抓取的文章ID集合）。"""
        path = self._checkpoint_path()
        with open(path, "wb") as f:
            pickle.dump(completed_ids, f)
        logger.debug("检查点已保存: %d 个ID", len(completed_ids))

    def load_checkpoint(self) -> set[str]:
        """加载检查点。"""
        path = self._checkpoint_path()
        if not path.exists():
            return set()
        try:
            with open(path, "rb") as f:
                ids = pickle.load(f)
            logger.info("从检查点恢复: %d 个已完成ID", len(ids))
            return ids
        except Exception:
            logger.warning("检查点损坏，将从头开始")
            return set()

    def clear_checkpoint(self) -> None:
        """清除检查点文件。"""
        path = self._checkpoint_path()
        if path.exists():
            path.unlink()
            logger.info("检查点已清除")

    # ── 统计 ───────────────────────────────────────────────

    def print_stats(self, articles: list[ArticleItem]) -> None:
        """打印数据集统计信息。"""
        if not articles:
            return

        dates = [a.publish_date for a in articles if a.publish_date]
        sources = set(a.source for a in articles if a.source)

        print("\n" + "=" * 60)
        print("  数据集统计")
        print("=" * 60)
        print(f"  总文章数:     {len(articles)}")
        if dates:
            print(f"  时间范围:     {min(dates)} ~ {max(dates)}")
        if sources:
            print(f"  来源数量:     {len(sources)}")
        print(f"  有正文:       {sum(1 for a in articles if a.content_text)}")

        total_chars = sum(len(a.content_text) for a in articles)
        print(f"  正文总字数:   {total_chars:,}")
        print("=" * 60)
