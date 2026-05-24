"""
HTML 解析器模块。

负责从列表页和文章页的 HTML 中提取结构化数据。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from .utils import logger


# ─── 数据模型 ──────────────────────────────────────────────


@dataclass
class ArticleItem:
    """单篇税案通报的结构化数据。"""

    article_id: str = ""               # 文章唯一ID（从URL提取）
    title: str = ""                    # 标题
    url: str = ""                      # 完整URL
    publish_date: str = ""             # 发布日期 YYYY-MM-DD
    source: str = ""                   # 来源（如"国家税务总局办公厅"）
    content_html: str = ""             # 正文HTML
    content_text: str = ""             # 正文纯文本
    editor: str = ""                   # 责任编辑
    crawler_ts: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ListItem:
    """列表页条目（不含正文）。"""

    article_id: str = ""
    title: str = ""
    url: str = ""
    publish_date: str = ""


# ─── 列表页解析 ────────────────────────────────────────────


class ListPageParser:
    """解析税案通报列表页 HTML。

    Parameters
    ----------
    base_url : str
        用于补全相对路径的基础URL。
    """

    def __init__(self, base_url: str = "https://www.chinatax.gov.cn") -> None:
        self.base_url = base_url.rstrip("/")

    def parse(self, html: str) -> list[ListItem]:
        """从列表页 HTML 提取所有文章条目。

        Returns
        -------
        list[ListItem]
        """
        soup = BeautifulSoup(html, "lxml")
        items: list[ListItem] = []

        # 列表容器：ul.list > li
        list_ul = soup.find("ul", class_="list")
        if not list_ul:
            logger.warning("未找到列表容器 ul.list")
            return items

        for li in list_ul.find_all("li", recursive=False):
            item = self._parse_li(li)
            if item and item.url:
                items.append(item)

        logger.debug("列表页解析完成，提取 %d 条", len(items))
        return items

    def _parse_li(self, li: Tag) -> ListItem | None:
        """解析单个 <li> 元素。"""
        # 链接 <a href="...">标题</a>
        a_tag = li.find("a", href=True)
        if not a_tag:
            return None

        href = a_tag["href"]
        title = a_tag.get_text(strip=True)

        # 补全URL
        if href.startswith("http"):
            full_url = href
        elif href.startswith("//"):
            full_url = "https:" + href
        else:
            full_url = self.base_url + href

        # 提取 article_id（URL 中 cXXXXXXX 部分）
        article_id = self._extract_article_id(full_url)

        # 日期 <span>[YYYY-MM-DD]</span>
        date_span = li.find("span")
        publish_date = ""
        if date_span:
            date_text = date_span.get_text(strip=True)
            m = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
            if m:
                publish_date = m.group(1)

        return ListItem(
            article_id=article_id,
            title=title,
            url=full_url,
            publish_date=publish_date,
        )

    @staticmethod
    def _extract_article_id(url: str) -> str:
        """从URL提取文章ID，如 'c5249875'。"""
        m = re.search(r"/c(\d{7,})/", url)
        return f"c{m.group(1)}" if m else ""

    def extract_total_pages(self, html: str) -> int:
        """尝试从分页信息中提取总页数。"""
        soup = BeautifulSoup(html, "lxml")
        # 查找 "共55页" 模式
        text = soup.get_text()
        m = re.search(r"共(\d+)页", text)
        return int(m.group(1)) if m else 55


# ─── 文章页解析 ────────────────────────────────────────────


class ArticleParser:
    """解析单篇税案通报的文章页 HTML。

    文章页的 `<meta>` 标签包含丰富元数据，
    正文在 ``#zoomcon`` 容器内。
    """

    def parse(self, html: str, url: str = "") -> ArticleItem:
        """从文章页 HTML 提取完整结构化数据。

        Parameters
        ----------
        html : str
            文章页完整HTML。
        url : str
            文章URL，用于提取ID。

        Returns
        -------
        ArticleItem
        """
        soup = BeautifulSoup(html, "lxml")

        # ── 元数据 ──
        title = self._meta(soup, "ArticleTitle")
        publish_date = self._meta(soup, "PubDate")
        source = self._meta(soup, "ContentSource")
        article_id = self._extract_article_id(url)

        # 日期格式：可能带时间，截取日期部分
        if publish_date:
            publish_date = publish_date[:10]  # "2026-05-22"

        # fallback: 从页面元素提取标题
        if not title:
            h1 = soup.find("div", class_="sv_texth1")
            if h1:
                title = h1.get_text(strip=True)

        # ── 正文 ──
        zoom = soup.find("div", id="zoomcon")
        if not zoom:
            zoom = soup.find("div", class_="article-content")

        content_html = str(zoom) if zoom else ""
        content_text = zoom.get_text(separator="\n", strip=True) if zoom else ""

        # ── 责任编辑 ──
        editor = ""
        editor_span = soup.find("span", class_="editer")
        if editor_span:
            editor_b = editor_span.find("b")
            if editor_b:
                editor = editor_b.get_text(strip=True)

        return ArticleItem(
            article_id=article_id,
            title=title,
            url=url,
            publish_date=publish_date,
            source=source,
            content_html=content_html,
            content_text=content_text,
            editor=editor,
        )

    @staticmethod
    def _meta(soup: BeautifulSoup, name: str) -> str:
        """提取 <meta name="..." content="..."> 的值。"""
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return ""

    @staticmethod
    def _extract_article_id(url: str) -> str:
        m = re.search(r"/c(\d{7,})/", url)
        return f"c{m.group(1)}" if m else ""
