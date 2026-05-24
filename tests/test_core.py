"""测试套件。"""

from __future__ import annotations

import pytest

from chinatax_crawler.config import Config
from chinatax_crawler.parser import (
    ArticleItem,
    ArticleParser,
    ListItem,
    ListPageParser,
)
from chinatax_crawler.storage import Storage


# ─── 配置测试 ──────────────────────────────────────────────


class TestConfig:
    def test_default_config(self) -> None:
        cfg = Config()
        assert cfg.total_pages == 55
        assert cfg.request_delay == 1.0
        assert cfg.output_format == "json"

    def test_override(self) -> None:
        cfg = Config()
        cfg.request_delay = 3.0
        assert cfg.request_delay == 3.0


# ─── 解析器测试 ────────────────────────────────────────────


LIST_HTML_SAMPLE = """
<ul class="list">
<li>
    <a href="http://www.chinatax.gov.cn/chinatax/n810219/c102025/c5249875/content.html"
       target="_blank">税务部门集中曝光8起私户收款偷税案件</a>
    <span>[2026-05-22]</span>
</li>
<li>
    <a href="/chinatax/n810219/c102025/c5249874/content.html"
       target="_blank">多起私户收款偷逃税案件被曝光</a>
    <span>[2026-05-22]</span>
</li>
</ul>
"""

ARTICLE_HTML_SAMPLE = """
<html>
<head>
<meta name="ArticleTitle" content="税务部门集中曝光8起私户收款偷税案件"/>
<meta name="PubDate" content="2026-05-22 16:00:22"/>
<meta name="ContentSource" content="国家税务总局办公厅"/>
</head>
<body>
<div id="zoomcon">
<p>近年来，税务部门认真贯彻落实党中央、国务院决策部署。</p>
<p>一、<strong>内蒙古伊东集团西乌素煤炭有限责任公司私户收款偷税案件。</strong></p>
</div>
<span class="editer">责任编辑：<b>曾彪</b></span>
</body>
</html>
"""


class TestListPageParser:
    def test_parse_items(self) -> None:
        parser = ListPageParser()
        items = parser.parse(LIST_HTML_SAMPLE)
        assert len(items) == 2
        assert items[0].title == "税务部门集中曝光8起私户收款偷税案件"
        assert items[0].article_id == "c5249875"
        assert items[0].publish_date == "2026-05-22"
        assert "c5249875" in items[0].url

    def test_absolute_url(self) -> None:
        parser = ListPageParser(base_url="https://www.chinatax.gov.cn")
        items = parser.parse(LIST_HTML_SAMPLE)
        assert items[1].url.startswith("https://www.chinatax.gov.cn")

    def test_extract_total_pages(self) -> None:
        parser = ListPageParser()
        html = '<html><body>共55页</body></html>'
        assert parser.extract_total_pages(html) == 55


class TestArticleParser:
    def test_parse_article(self) -> None:
        parser = ArticleParser()
        url = "http://www.chinatax.gov.cn/chinatax/n810219/c102025/c5249875/content.html"
        article = parser.parse(ARTICLE_HTML_SAMPLE, url)

        assert article.article_id == "c5249875"
        assert article.title == "税务部门集中曝光8起私户收款偷税案件"
        assert article.publish_date == "2026-05-22"
        assert article.source == "国家税务总局办公厅"
        assert article.editor == "曾彪"
        assert "党中央" in article.content_text
        assert article.content_html.startswith("<div")


# ─── 存储测试 ──────────────────────────────────────────────


class TestStorage:
    def test_save_load_index(self, tmp_path) -> None:
        store = Storage(data_dir=tmp_path, output_name="test")
        items = [
            ListItem("c1", "标题1", "http://example.com/1", "2026-01-01"),
            ListItem("c2", "标题2", "http://example.com/2", "2026-01-02"),
        ]
        store.save_index(items)
        loaded = store.load_index()
        assert len(loaded) == 2
        assert loaded[0].article_id == "c1"

    def test_checkpoint(self, tmp_path, monkeypatch) -> None:
        from chinatax_crawler import config as cfg_module
        monkeypatch.setattr(cfg_module.config, "checkpoint_dir", tmp_path)

        store = Storage(data_dir=tmp_path, output_name="test")
        store.save_checkpoint({"c1", "c2", "c3"})
        loaded = store.load_checkpoint()
        assert loaded == {"c1", "c2", "c3"}

    def test_article_to_dict(self) -> None:
        article = ArticleItem(
            article_id="c123",
            title="测试标题",
            url="http://example.com",
            publish_date="2026-01-01",
        )
        d = article.to_dict()
        assert d["article_id"] == "c123"
        assert "crawler_ts" in d
