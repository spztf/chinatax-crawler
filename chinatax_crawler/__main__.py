"""
命令行入口模块。

用法::

    python -m chinatax_crawler [选项]

    --list          仅抓取文章索引列表
    --full          完整抓取（列表 + 文章正文）【默认】
    --format FORMAT 输出格式: json, jsonl, csv
    --delay FLOAT   请求间隔秒数 (默认 1.0)
    --max N         最多抓取 N 篇文章
    --no-resume     禁用断点续传
    --log-level     日志级别: DEBUG, INFO, WARNING, ERROR
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config, config
from .crawler import Crawler
from .storage import Storage


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    p = argparse.ArgumentParser(
        prog="chinatax-crawler",
        description="国家税务总局「税案通报」栏目爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m chinatax_crawler                    # 完整抓取
    python -m chinatax_crawler --list             # 仅抓取索引
    python -m chinatax_crawler --format csv       # 输出CSV
    python -m chinatax_crawler --max 50           # 只抓50篇测试
    python -m chinatax_crawler --delay 2.0        # 慢速抓取，间隔2秒
    python -m chinatax_crawler --no-resume        # 禁用断点续传
        """,
    )

    # 模式
    mode = p.add_argument_group("爬取模式")
    mode.add_argument(
        "--list", action="store_true",
        help="仅抓取文章索引列表（不含正文）",
    )
    mode.add_argument(
        "--full", action="store_true", default=True,
        help="完整抓取：列表 + 文章正文（默认）",
    )

    # 输出
    output = p.add_argument_group("输出选项")
    output.add_argument(
        "--format", choices=["json", "jsonl", "csv"],
        default="json", help="输出格式（默认: json）",
    )
    output.add_argument(
        "--output", "-o", type=str, default=None,
        help="输出文件名（不含扩展名）",
    )
    output.add_argument(
        "--data-dir", type=str, default=None,
        help="数据输出目录",
    )

    # 请求控制
    req = p.add_argument_group("请求控制")
    req.add_argument(
        "--delay", type=float, default=None,
        help="请求间隔秒数（默认: 1.0）",
    )
    req.add_argument(
        "--timeout", type=int, default=None,
        help="请求超时秒数（默认: 30）",
    )
    req.add_argument(
        "--max", dest="max_articles", type=int, default=0,
        help="最多抓取文章数（0=不限制）",
    )
    req.add_argument(
        "--no-resume", action="store_true",
        help="禁用断点续传，从头开始抓取",
    )

    # 其他
    other = p.add_argument_group("其他")
    other.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO", help="日志级别（默认: INFO）",
    )
    other.add_argument(
        "--log-file", type=str, default=None,
        help="日志文件路径",
    )
    other.add_argument(
        "--version", action="version",
        version="chinatax-crawler 0.1.0",
    )

    return p


def merge_config(args: argparse.Namespace) -> Config:
    """将命令行参数合并到配置对象中。"""
    cfg = Config()  # 新建实例（保留环境变量覆盖）

    # 逐字段覆盖
    overrides: dict = {}

    if args.delay is not None:
        overrides["request_delay"] = args.delay
    if args.timeout is not None:
        overrides["request_timeout"] = args.timeout
    if args.max_articles:
        overrides["max_articles"] = args.max_articles
    if args.no_resume:
        overrides["resume"] = False
    if args.list:
        overrides["list_only"] = True
    if args.format:
        overrides["output_format"] = args.format
    if args.output:
        overrides["output_name"] = args.output
    if args.data_dir:
        overrides["data_dir"] = Path(args.data_dir)
    if args.log_level:
        overrides["log_level"] = args.log_level
    if args.log_file:
        overrides["log_file"] = Path(args.log_file)

    for k, v in overrides.items():
        setattr(cfg, k, v)

    # 确保目录
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    return cfg


def main(argv: list[str] | None = None) -> int:
    """主入口。

    Returns
    -------
    int
        退出码。0=成功，1=失败。
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = merge_config(args)

    # 重新初始化日志
    from .utils import setup_logging
    setup_logging(cfg.log_level, str(cfg.log_file) if cfg.log_file else None)

    crawler = Crawler(cfg)

    try:
        if cfg.list_only:
            items = crawler.run_list_only()
            print(f"\n[OK] 索引完成！共 {len(items)} 篇文章。")
            print(f"  数据文件: {cfg.data_dir / f'{cfg.output_name}_index.json'}")
        else:
            crawler.run_full()
            print(f"\n[OK] 爬取完成！")
            print(f"  数据文件: {cfg.data_dir / f'{cfg.output_name}.json'}")
    except KeyboardInterrupt:
        print("\n\n[WARN] 用户中断。检查点已保存，下次运行将继续。")
        return 130
    except Exception as exc:
        print(f"\n[ERROR] 错误: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
