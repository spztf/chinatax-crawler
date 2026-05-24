"""Step 2: Fetch article bodies (batched, resumable)."""
import sys
sys.path.insert(0, ".")

from chinatax_crawler.config import Config
from chinatax_crawler.crawler import Crawler

cfg = Config()
cfg.request_delay = 0.3
cfg.request_timeout = 20
cfg.max_articles = 300  # per batch
cfg.resume = True
cfg.log_level = "INFO"

crawler = Crawler(cfg)
crawler.run_full()
print("\n[DONE] Batch complete. Run again for next batch.")
