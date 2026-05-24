"""Batch runner for chinatax-crawler."""
import sys
sys.path.insert(0, ".")

from chinatax_crawler.config import Config
from chinatax_crawler.crawler import Crawler

cfg = Config()
cfg.request_delay = 0.3
cfg.request_timeout = 20
cfg.max_articles = 300
cfg.resume = True
cfg.log_level = "INFO"

crawler = Crawler(cfg)
crawler.run_full()
print("\n[DONE] Batch complete.")
