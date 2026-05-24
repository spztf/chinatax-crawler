"""
爬虫引擎模块。

负责编排整个爬取流程：列表页 → 文章链接 → 文章正文。
支持断点续传、增量抓取、进度展示。
"""

from __future__ import annotations

import time
from typing import Callable

import requests
from tqdm import tqdm

from .config import config
from .parser import (
    ArticleItem,
    ArticleParser,
    ListItem,
    ListPageParser,
)
from .storage import Storage
from .utils import (
    create_session,
    logger,
    retry_on_failure,
    rate_limit,
)


class Crawler:
    """国家税务总局税案通报爬虫。

    Parameters
    ----------
    cfg : Config | None
        爬虫配置。若为 None 则使用全局默认配置。

    Usage::

        crawler = Crawler()
        articles = crawler.run_full()  # 完整流程
    """

    def __init__(self, cfg=None) -> None:  # type: ignore[no-untyped-def]
        self.cfg = cfg or config
        self.session = create_session()
        self.list_parser = ListPageParser(base_url=self.cfg.base_url)
        self.article_parser = ArticleParser()
        self.storage = Storage()
        self._stats: dict[str, int] = {"list_pages": 0, "articles": 0, "errors": 0}

    # ── 公开 API ───────────────────────────────────────────

    def run_list_only(self) -> list[ListItem]:
        """仅抓取列表页，返回所有文章索引（不抓正文）。

        Returns
        -------
        list[ListItem]
            所有文章的基本信息。
        """
        all_items = self._fetch_all_list_pages()
        self.storage.save_index(all_items)
        self.storage.save_csv(all_items)  # type: ignore[arg-type]
        return all_items

    def run_full(self, progress_callback: Callable | None = None) -> list[ArticleItem]:
        """完整流程：抓取列表 → 逐篇抓取正文 → 保存。

        Parameters
        ----------
        progress_callback : callable | None
            每完成一篇文章时的回调，签名为 (current, total)。

        Returns
        -------
        list[ArticleItem]
        """
        # 1. 获取索引
        items = self._get_index()

        # 2. 加载检查点
        completed_ids: set[str] = set()
        articles: list[ArticleItem] = []
        if self.cfg.resume:
            completed_ids = self.storage.load_checkpoint()
            # 从已有JSONL恢复已完成数据
            jsonl_path = self.storage.data_dir / f"{self.cfg.output_name}.jsonl"
            if jsonl_path.exists() and completed_ids:
                logger.info("发现已有数据文件，将继续追加")

        # 3. 过滤未完成的
        todo = [i for i in items if i.article_id not in completed_ids]
        if self.cfg.max_articles > 0:
            todo = todo[:self.cfg.max_articles]
        if not todo:
            logger.info("全部文章已抓取完毕！")
            return articles

        logger.info("待抓取: %d 篇 (已完成: %d)", len(todo), len(completed_ids))

        # 4. 逐篇抓取
        pbar = tqdm(todo, desc="抓取文章", unit="篇", ncols=100)
        for idx, item in enumerate(pbar, start=1):
            try:
                article = self._fetch_article(item)
                articles.append(article)

                # 增量写入 JSONL
                self.storage.append_jsonl(article)

                # 定期保存检查点
                if idx % self.cfg.checkpoint_interval == 0:
                    completed_ids.add(item.article_id)
                    self.storage.save_checkpoint(
                        completed_ids | {a.article_id for a in articles}
                    )

                if progress_callback:
                    progress_callback(idx, len(todo))

            except Exception as exc:
                logger.error("抓取失败 [%s]: %s", item.article_id, exc)
                self._stats["errors"] += 1

            finally:
                # 速率限制
                time.sleep(self.cfg.request_delay)

        pbar.close()

        # 5. 最终保存
        completed_ids |= {a.article_id for a in articles}
        self.storage.save_checkpoint(completed_ids)

        # 保存完整JSON
        all_articles = self._load_existing_articles() + articles
        self.storage.save_json(all_articles)

        # 统计
        self.storage.print_stats(all_articles)
        logger.info(
            "完成！共 %d 篇，列表页 %d 页，错误 %d 次",
            len(all_articles),
            self._stats["list_pages"],
            self._stats["errors"],
        )
        return articles

    # ── 内部方法 ────────────────────────────────────────────

    def _get_index(self) -> list[ListItem]:
        """获取文章索引（优先从缓存加载）。"""
        cached = self.storage.load_index()
        if cached:
            logger.info("从缓存加载索引: %d 条", len(cached))
            return cached
        return self._fetch_all_list_pages()

    @retry_on_failure()
    @rate_limit()
    def _fetch_page_html(self, url: str) -> str:
        """抓取单页HTML（带重试和限速）。"""
        resp = self.session.get(url, timeout=self.cfg.request_timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    def _fetch_all_list_pages(self) -> list[ListItem]:
        """遍历所有列表页，提取全部文章索引。"""
        all_items: list[ListItem] = []
        seen_ids: set[str] = set()

        # 先用第1页探测真实总页数
        first_url = self.cfg.list_url_template.format(page=1)
        first_html = self._fetch_page_html(first_url)
        total_pages = self.list_parser.extract_total_pages(first_html)
        logger.info("检测到总页数: %d", total_pages)

        pbar = tqdm(
            range(1, total_pages + 1),
            desc="抓取列表页",
            unit="页",
            ncols=100,
        )

        for page in pbar:
            try:
                if page == 1:
                    html = first_html
                else:
                    url = self.cfg.list_url_template.format(page=page)
                    html = self._fetch_page_html(url)
                    time.sleep(self.cfg.request_delay)

                items = self.list_parser.parse(html)

                # 去重
                new_count = 0
                for item in items:
                    if item.article_id and item.article_id not in seen_ids:
                        seen_ids.add(item.article_id)
                        all_items.append(item)
                        new_count += 1

                self._stats["list_pages"] = page
                pbar.set_postfix({"本页": len(items), "累计": len(all_items)})

            except requests.RequestException as exc:
                logger.error("列表页 %d 抓取失败: %s", page, exc)
                self._stats["errors"] += 1
                # 失败时跳过该页继续
                continue

        pbar.close()
        logger.info("列表索引完成: %d 条", len(all_items))
        return all_items

    def _fetch_article(self, item: ListItem) -> ArticleItem:
        """根据 ListItem 抓取文章正文。"""
        html = self._fetch_page_html(item.url)
        return self.article_parser.parse(html, item.url)

    def _load_existing_articles(self) -> list[ArticleItem]:
        """从已有 JSON 文件加载已抓取的文章。"""
        path = self.storage.data_dir / f"{self.cfg.output_name}.json"
        if not path.exists():
            return []
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            ArticleItem(
                article_id=d.get("article_id", ""),
                title=d.get("title", ""),
                url=d.get("url", ""),
                publish_date=d.get("publish_date", ""),
                source=d.get("source", ""),
                content_html=d.get("content_html", ""),
                content_text=d.get("content_text", ""),
                editor=d.get("editor", ""),
                crawler_ts=d.get("crawler_ts", ""),
            )
            for d in data
        ]
