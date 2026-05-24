"""续抓脚本 —— 从检查点恢复，高效抓取剩余文章。"""
import json
import pickle
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

# ── 配置 ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
INDEX_FILE = DATA_DIR / "chinatax_cases_index.json"
JSONL_FILE = DATA_DIR / "chinatax_cases.jsonl"
JSON_FILE = DATA_DIR / "chinatax_cases.json"
CP_DIR = DATA_DIR / "checkpoint"
CP_FILE = CP_DIR / "chinatax_cases_checkpoint.pkl"

DELAY = 0.25          # 请求间隔（秒）
TIMEOUT = 20          # 请求超时（秒）
MAX_RETRIES = 3       # 最大重试次数
BATCH_SAVE = 50       # 每 N 篇保存一次检查点
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


def load_checkpoint():
    if CP_FILE.exists():
        with open(CP_FILE, "rb") as f:
            return pickle.load(f)
    return set()


def save_checkpoint(done):
    CP_DIR.mkdir(parents=True, exist_ok=True)
    with open(CP_FILE, "wb") as f:
        pickle.dump(done, f)


def load_existing_jsonl():
    """从 JSONL 恢复已有记录（用于重建 json）"""
    records = []
    if JSONL_FILE.exists():
        with open(JSONL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return records


def fetch_article(url):
    """抓取单篇文章，返回 (success, data_dict)"""
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                return True, parse_article(soup, url)
            else:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 * (attempt + 1))
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 * (attempt + 1))
            else:
                print(f"  [ERROR] {url}: {e}")
    return False, None


def parse_article(soup, url):
    """解析文章详情页"""
    data = {"url": url}

    # 标题
    title_tag = soup.select_one(".xxgk_title, .article-title, h2")
    if title_tag:
        data["title"] = title_tag.get_text(strip=True)
    else:
        data["title"] = ""

    # 发布日期 & 来源
    info_tag = soup.select_one(".xxgk_time, .article-info, .info")
    if info_tag:
        info_text = info_tag.get_text(strip=True)
        # 提取日期
        import re
        date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', info_text)
        if date_match:
            data["publish_date"] = date_match.group(1).replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-")
        else:
            data["publish_date"] = ""
        # 提取来源
        src_match = re.search(r'来源[：:]\s*(.+?)(?:\s|$)', info_text)
        if src_match:
            data["source"] = src_match.group(1).strip()
        else:
            data["source"] = ""
    else:
        data["publish_date"] = ""
        data["source"] = ""

    # 正文
    content_tag = soup.select_one(".xxgk_cont1, .article-content, .TRS_Editor, #zoom, .content")
    if content_tag:
        data["content_text"] = content_tag.get_text(separator="\n", strip=True)
    else:
        data["content_text"] = ""

    # article_id
    import re
    id_match = re.search(r'/([^/]+)\.html$', url)
    data["article_id"] = id_match.group(1) if id_match else url.rsplit("/", 1)[-1]

    return data


def append_jsonl(record):
    with open(JSONL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def sync_main_json():
    """用 JSONL 同步主 JSON 文件"""
    records = load_existing_jsonl()
    records.sort(key=lambda r: r.get("publish_date", ""), reverse=True)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return len(records)


def main():
    # 加载索引
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)
    print(f"[*] 索引总数: {len(index)}")

    # 加载检查点
    done = load_checkpoint()
    print(f"[*] 已完成: {len(done)}")

    # 过滤待抓取
    pending = [(a["article_id"], a["url"]) for a in index if a["article_id"] not in done]
    print(f"[*] 待抓取: {len(pending)}")

    if not pending:
        print("[✓] 全部完成！同步 JSON 文件...")
        count = sync_main_json()
        print(f"[✓] JSON 同步完成: {count} 篇")
        return

    start_time = time.time()
    deadline = start_time + 540  # 9 分钟（留 1 分钟余量）

    new_count = 0
    for i, (aid, url) in enumerate(pending):
        # 检查时间
        if time.time() > deadline:
            remaining = len(pending) - i
            print(f"\n[⏱] 时间到，剩余 {remaining} 篇。检查点已保存。")
            break

        print(f"[{i+1}/{len(pending)}] {aid[:50]}... ", end="", flush=True)
        ok, data = fetch_article(url)

        if ok and data and data.get("content_text"):
            append_jsonl(data)
            done.add(aid)
            new_count += 1
            print(f"✓ ({len(data['content_text'])}字)")
        else:
            # 即使没内容也标记为已处理（避免死循环）
            done.add(aid)
            print("✗")

        # 定期保存检查点
        if new_count > 0 and new_count % BATCH_SAVE == 0:
            save_checkpoint(done)
            print(f"  [ checkpoint saved: {len(done)}/{len(index)} ]")

        time.sleep(DELAY)

    # 保存最终检查点
    save_checkpoint(done)
    print(f"\n[*] 本轮新增: {new_count}")
    print(f"[*] 总计完成: {len(done)}/{len(index)}")

    # 同步主 JSON
    count = sync_main_json()
    print(f"[*] JSON 同步完成: {count} 篇")


if __name__ == "__main__":
    main()
