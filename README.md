# chinatax-crawler

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**国家税务总局「税案通报」栏目爬虫**

从 [国家税务总局网站](https://www.chinatax.gov.cn/chinatax/manuscriptList/c102025) 的「税案通报」栏目自动抓取税务案例数据，输出结构化 JSON / JSONL / CSV 数据集。

## 功能特性

- 🔍 **自动发现** — 自动检测总页数，无需手动指定
- 📄 **正文提取** — 解析文章页 HTML，提取标题、正文、来源、日期、责任编辑
- 📊 **多格式导出** — 支持 JSON、JSONL（适合大数据集）、CSV 三种格式
- ⏸️ **断点续传** — 中断后自动从检查点恢复，不重复抓取
- 🔄 **自动重试** — 指数退避重试，应对网络波动
- 📈 **进度条** — tqdm 实时显示进度
- 🎛️ **灵活配置** — CLI 参数 + 环境变量双重覆盖
- 📦 **轻量依赖** — 仅需 `requests` + `beautifulsoup4` + `tqdm` + `lxml`

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/user/chinatax-crawler.git
cd chinatax-crawler

# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -e .
```

### 基本使用

```bash
# 完整抓取（列表 + 文章正文）→ data/chinatax_cases.json
python -m chinatax_crawler

# 仅抓取索引列表 → data/chinatax_cases_index.json
python -m chinatax_crawler --list

# 输出 CSV 格式
python -m chinatax_crawler --format csv

# 测试模式：只抓取前 20 篇
python -m chinatax_crawler --max 20

# 慢速抓取（间隔 2 秒），避免被限流
python -m chinatax_crawler --delay 2.0
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--list` | 仅抓取索引（不抓正文） | — |
| `--format json\|jsonl\|csv` | 输出格式 | `json` |
| `--output, -o NAME` | 输出文件名（不含扩展名） | `chinatax_cases` |
| `--data-dir DIR` | 数据输出目录 | `./data` |
| `--delay FLOAT` | 请求间隔（秒） | `1.0` |
| `--timeout INT` | 请求超时（秒） | `30` |
| `--max N` | 最多抓取 N 篇文章 | `0`（不限） |
| `--no-resume` | 禁用断点续传 | — |
| `--log-level DEBUG\|INFO\|...` | 日志级别 | `INFO` |
| `--log-file PATH` | 日志文件路径 | — |

### 环境变量

所有配置项均可通过环境变量 `CHINATAX_*` 覆盖：

```bash
# Windows PowerShell
$env:CHINATAX_REQUEST_DELAY = "2.0"
$env:CHINATAX_OUTPUT_FORMAT = "csv"

# Linux/macOS
export CHINATAX_REQUEST_DELAY=2.0
export CHINATAX_OUTPUT_FORMAT=csv
```

## 输出数据格式

### JSON (`chinatax_cases.json`)

```json
[
  {
    "article_id": "c5249875",
    "title": "税务部门集中曝光8起私户收款偷税案件",
    "url": "http://www.chinatax.gov.cn/chinatax/n810219/c102025/c5249875/content.html",
    "publish_date": "2026-05-22",
    "source": "国家税务总局办公厅",
    "content_html": "<p>...</p>",
    "content_text": "近年来，税务部门认真贯彻...",
    "editor": "曾彪",
    "crawler_ts": "2025-01-15T10:30:00.123456"
  }
]
```

### CSV (`chinatax_cases.csv`)

| article_id | title | url | publish_date | source | editor | content_text |
|------------|-------|-----|-------------|--------|--------|-------------|
| c5249875 | 税务部门集中曝光... | http://... | 2026-05-22 | 国家税务总局办公厅 | 曾彪 | 近年来... |

## 项目结构

```
chinatax-crawler/
├── chinatax_crawler/
│   ├── __init__.py      # 包入口
│   ├── __main__.py      # CLI 接口
│   ├── config.py        # 配置管理
│   ├── crawler.py       # 爬虫引擎
│   ├── parser.py        # HTML 解析器
│   ├── storage.py       # 数据存储
│   └── utils.py         # 工具函数
├── data/                # 输出数据（gitignored）
├── tests/               # 测试
├── pyproject.toml       # 项目元数据
├── README.md
├── LICENSE
└── .gitignore
```

## 数据规模

- 约 **55 页** 列表
- 每页约 **20 篇** 文章
- 总计约 **1,100 篇** 税案通报
- 覆盖时间范围：约 2017 年至今

## 注意事项

1. **遵守 robots.txt** — 本爬虫遵循目标网站的爬取规则
2. **合理速率** — 默认请求间隔 1 秒，请勿设置过低
3. **非商业用途** — 数据版权归国家税务总局所有，请合理使用
4. **网络环境** — 部分网络可能需要代理访问 gov.cn 域名

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 代码检查
ruff check chinatax_crawler/

# 运行测试
pytest tests/ -v
```

## License

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

> ⚠️ **免责声明**：本项目仅用于学习和研究目的。爬取的数据版权归 [国家税务总局](https://www.chinatax.gov.cn) 所有。使用者应遵守相关法律法规和目标网站的 robots.txt 规定。
