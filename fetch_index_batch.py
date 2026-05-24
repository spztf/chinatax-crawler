"""Robust batch index fetcher — fetches list pages in small batches, saves incrementally.

Usage:
    python fetch_index_batch.py          # auto-resume, 5 pages per batch
    python fetch_index_batch.py --all    # fetch all 55 pages at once
    python fetch_index_batch.py --start 1 --count 5   # specific range
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.chinatax.gov.cn"
LIST_URL = BASE_URL + "/chinatax/manuscriptList/c102025"
PARAMS_TEMPLATE = {
    "_channelName": "税案通报",
    "_isAgg": "0",
    "_pageSize": "20",
    "_template": "index",
    "_keyWH": "wenhao",
}
# Note: pagination uses "page=" (NOT "_pageIndex=")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = DATA_DIR / "chinatax_cases_index.json"
PROGRESS_PATH = DATA_DIR / "index_progress.json"


def fetch_page(page: int, session: requests.Session) -> str | None:
    """Fetch one list page HTML. Returns None on failure."""
    params = {**PARAMS_TEMPLATE, "_pageIndex": str(page)}
    try:
        r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=25)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except Exception as e:
        print(f"  [ERR] page {page}: {e}")
        return None


def parse_page(html: str) -> list[dict]:
    """Extract article entries from list page HTML."""
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []
    ul = soup.find("ul", class_="list")
    if not ul:
        return items

    for li in ul.find_all("li", recursive=False):
        a = li.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        title = a.get_text(strip=True)
        url = href if href.startswith("http") else (BASE_URL + href)

        m = re.search(r"/c(\d{7,})/", url)
        article_id = f"c{m.group(1)}" if m else ""

        span = li.find("span")
        date_str = ""
        if span:
            dm = re.search(r"(\d{4}-\d{2}-\d{2})", span.get_text(strip=True))
            if dm:
                date_str = dm.group(1)

        items.append({
            "article_id": article_id,
            "title": title,
            "url": url,
            "publish_date": date_str,
        })
    return items


def detect_total_pages(html: str) -> int:
    m = re.search(r"共(\d+)页", html)
    return int(m.group(1)) if m else 55


def load_index() -> list[dict]:
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_index(items: list[dict]) -> None:
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def load_progress() -> set[int]:
    if PROGRESS_PATH.exists():
        with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_progress(pages: set[int]) -> None:
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(pages), f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="Fetch all pages")
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--delay", type=float, default=0.5)
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update(HEADERS)

    # Load state
    all_items = load_index()
    seen_ids = {it["article_id"] for it in all_items}
    fetched_pages = load_progress()

    # Determine page range
    if args.all:
        # First fetch page 1 to detect total
        print("Fetching page 1 to detect total...")
        html = fetch_page(1, session)
        if html:
            total = detect_total_pages(html)
            items = parse_page(html)
            for it in items:
                if it["article_id"] not in seen_ids:
                    seen_ids.add(it["article_id"])
                    all_items.append(it)
            fetched_pages.add(1)
            save_index(all_items)
            save_progress(fetched_pages)
            print(f"  Page 1: {len(items)} items, total pages={total}")

        todo = [p for p in range(2, total + 1) if p not in fetched_pages]
    elif args.start:
        todo = list(range(args.start, args.start + args.count))
    else:
        # Default: find next un-fetched pages (up to 5)
        if not fetched_pages:
            todo = [1]
        else:
            max_done = max(fetched_pages)
            todo = [p for p in range(max_done + 1, max_done + 1 + args.count)]

    if not todo:
        print("All pages already fetched!")
        return

    print(f"Will fetch pages: {todo[0]}..{todo[-1]} ({len(todo)} pages)")
    print(f"Current index: {len(all_items)} items\n")

    for i, page in enumerate(todo):
        sys.stdout.write(f"[{i+1}/{len(todo)}] Page {page} ... ")
        sys.stdout.flush()

        html = fetch_page(page, session)
        if html is None:
            print("SKIPPED")
            continue

        if page == 1:
            total = detect_total_pages(html)
            print(f"OK (total={total})")
        else:
            print("OK")

        items = parse_page(html)
        new = 0
        for it in items:
            if it["article_id"] not in seen_ids:
                seen_ids.add(it["article_id"])
                all_items.append(it)
                new += 1

        fetched_pages.add(page)
        print(f"       -> {len(items)} raw, {new} new, {len(all_items)} total")

        # Save after each page
        save_index(all_items)
        save_progress(fetched_pages)

        if i < len(todo) - 1:
            time.sleep(args.delay)

    print(f"\nDONE. Index now has {len(all_items)} entries from {len(fetched_pages)} pages.")


if __name__ == "__main__":
    main()
