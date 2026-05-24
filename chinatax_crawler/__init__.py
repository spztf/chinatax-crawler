"""
chinatax-crawler — 国家税务总局税案通报爬虫
============================================

从国家税务总局网站「税案通报」栏目爬取税务案例数据，
支持增量抓取、断点续传、多格式导出。

Usage::

    python -m chinatax_crawler          # 默认：抓取列表+文章，存JSON
    python -m chinatax_crawler --list   # 仅抓取索引列表
    python -m chinatax_crawler --full   # 完整抓取（含文章正文）
    python -m chinatax_crawler --format csv  # 导出为CSV
"""

__version__ = "0.1.0"
__all__ = [
    "Crawler",
    "ListPageParser",
    "ArticleParser",
    "Storage",
    "Config",
    "__version__",
]
