# chinatax-crawler

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![中文](https://img.shields.io/badge/README-中文-red.svg)](README.md)

**Web crawler for the "Tax Case Bulletin" column of China's State Taxation Administration**

Automatically scrapes tax case data from the [State Taxation Administration website](https://www.chinatax.gov.cn/chinatax/manuscriptList/c102025) ("Tax Case Bulletin" section), outputting structured datasets in JSON / JSONL / CSV formats.

> 📖 [中文版本 →](README.md)

## Features

- 🔍 **Auto-discovery** — Automatically detects total page count; no manual configuration needed
- 📄 **Full-text extraction** — Parses article pages to extract title, body, source, date, and editor
- 📊 **Multi-format export** — JSON, JSONL (recommended for large datasets), and CSV output
- ⏸️ **Resumable** — Checkpoint-based resume; never re-scrape already-fetched articles
- 🔄 **Auto-retry** — Exponential backoff to handle network instability
- 📈 **Progress bar** — Real-time progress via tqdm
- 🎛️ **Flexible configuration** — CLI arguments + environment variable overrides
- 📦 **Lightweight** — Only depends on `requests` + `beautifulsoup4` + `tqdm` + `lxml`

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/spztf/chinatax-crawler.git
cd chinatax-crawler

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows

# Install dependencies
pip install -e .
```

### Basic Usage

```bash
# Full scrape (index + article bodies) → data/chinatax_cases.json
python -m chinatax_crawler

# Index-only mode → data/chinatax_cases_index.json
python -m chinatax_crawler --list

# Export as CSV
python -m chinatax_crawler --format csv

# Test mode: scrape only the first 20 articles
python -m chinatax_crawler --max 20

# Slow mode (2-second delay) to avoid rate limiting
python -m chinatax_crawler --delay 2.0
```

### CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--list` | Index-only mode (skip article bodies) | — |
| `--format json\|jsonl\|csv` | Output format | `json` |
| `--output, -o NAME` | Output filename (without extension) | `chinatax_cases` |
| `--data-dir DIR` | Output directory | `./data` |
| `--delay FLOAT` | Delay between requests (seconds) | `1.0` |
| `--timeout INT` | Request timeout (seconds) | `30` |
| `--max N` | Maximum articles to scrape | `0` (unlimited) |
| `--no-resume` | Disable checkpoint/resume | — |
| `--log-level DEBUG\|INFO\|...` | Logging level | `INFO` |
| `--log-file PATH` | Log file path | — |

### Environment Variables

All settings can be overridden via `CHINATAX_*` environment variables:

```bash
# Linux/macOS
export CHINATAX_REQUEST_DELAY=2.0
export CHINATAX_OUTPUT_FORMAT=csv

# Windows PowerShell
$env:CHINATAX_REQUEST_DELAY = "2.0"
$env:CHINATAX_OUTPUT_FORMAT = "csv"
```

## Output Data Format

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

## Project Structure

```
chinatax-crawler/
├── chinatax_crawler/
│   ├── __init__.py      # Package entry point
│   ├── __main__.py      # CLI interface
│   ├── config.py        # Configuration management
│   ├── crawler.py       # Crawler engine
│   ├── parser.py        # HTML parser
│   ├── storage.py       # Data storage / I/O
│   └── utils.py         # Utility functions
├── data/                # Output data (gitignored)
├── tests/               # Unit tests
├── pyproject.toml       # Project metadata
├── README.md            # Chinese documentation
├── README_EN.md         # English documentation (this file)
├── LICENSE
└── .gitignore
```

## Dataset Size

- ~ **55** list pages
- ~ **20** articles per page
- ~ **1,100** tax case bulletins in total
- Coverage: roughly 2017 to present

## Important Notes

1. **Respect robots.txt** — This crawler observes the target website's crawling rules
2. **Reasonable rate** — Default delay is 1 second; do not set it too low
3. **Non-commercial use** — Data copyright belongs to the State Taxation Administration; use responsibly
4. **Network access** — Some networks may require a proxy to access `gov.cn` domains

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Lint
ruff check chinatax_crawler/

# Run tests
pytest tests/ -v
```

## License

MIT License — see the [LICENSE](LICENSE) file for details.

---

> ⚠️ **Disclaimer**: This project is intended for educational and research purposes only. All scraped data is copyrighted by the [State Taxation Administration of China](https://www.chinatax.gov.cn). Users should comply with applicable laws, regulations, and the target website's robots.txt policies.
