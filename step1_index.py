"""Step 1: Fetch list index (all 55 pages)."""
import sys
sys.path.insert(0, ".")

from chinatax_crawler.config import Config
from chinatax_crawler.crawler import Crawler

cfg = Config()
cfg.request_delay = 0.3
cfg.request_timeout = 20
cfg.log_level = "INFO"

crawler = Crawler(cfg)
items = crawler.run_list_only()
print(f"\n[DONE] Index: {len(items)} articles from all pages.")
