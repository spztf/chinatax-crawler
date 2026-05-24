"""Dedup JSONL, rebuild JSON + CSV, and verify completeness."""
import json, csv, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent / "data"
INDEX_FILE = DATA_DIR / "chinatax_cases_index.json"
JSONL_FILE = DATA_DIR / "chinatax_cases.jsonl"
JSON_FILE = DATA_DIR / "chinatax_cases.json"
CSV_FILE = DATA_DIR / "chinatax_cases.csv"

# ── 1. Load index ──
with open(INDEX_FILE, encoding="utf-8") as f:
    index = json.load(f)
print(f"[1] Index: {len(index)} entries")

# ── 2. Load JSONL, dedup by article_id (keep longest content) ──
with open(JSONL_FILE, encoding="utf-8") as f:
    raw = [json.loads(line) for line in f if line.strip()]
print(f"[2] JSONL raw: {len(raw)} lines")

best = {}
for r in raw:
    aid = r.get("article_id", "")
    if aid:
        cur_len = len(r.get("content_text", ""))
        if aid not in best or cur_len > len(best[aid].get("content_text", "")):
            best[aid] = r

print(f"[3] Unique after dedup: {len(best)}")

# ── 3. Check coverage ──
index_ids = set(a["article_id"] for a in index)
have_ids = set(best.keys())
missing = index_ids - have_ids
extra = have_ids - index_ids

print(f"[4] Coverage:")
print(f"    Index:  {len(index_ids)}")
print(f"    Have:   {len(have_ids)}")
print(f"    Missing:{len(missing)}")
print(f"    Extra:  {len(extra)}")

if missing:
    print(f"    MISSING IDs: {list(missing)[:20]}...")
if extra:
    print(f"    EXTRA IDs (not in index): {list(extra)[:10]}")

# ── 4. Check for empty content ──
empty = [aid for aid, r in best.items() if not r.get("content_text", "").strip()]
print(f"[5] Empty content: {len(empty)}")

# ── 5. Write deduped JSONL ──
records = sorted(best.values(), key=lambda r: r.get("publish_date", ""), reverse=True)
with open(JSONL_FILE, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"[6] Deduped JSONL written: {len(records)} lines")

# ── 6. Write JSON ──
with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
print(f"[7] JSON written: {len(records)} records")

# ── 7. Write CSV ──
with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["article_id", "title", "url", "publish_date", "source", "content_text"])
    writer.writeheader()
    for r in records:
        writer.writerow({k: r.get(k, "") for k in ["article_id", "title", "url", "publish_date", "source", "content_text"]})
print(f"[8] CSV written: {len(records)} rows")

print("\n✅ Done! All 4 files are deduped and consistent.")
