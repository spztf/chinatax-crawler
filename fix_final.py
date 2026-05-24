"""Fix: remove the 'content' artifact record and rebuild all files."""
import json, csv

DATA = "data"

with open(f"{DATA}/chinatax_cases.jsonl", encoding="utf-8") as f:
    recs = [json.loads(line) for line in f if line.strip()]

clean = [r for r in recs if r.get("article_id") != "content"]
clean.sort(key=lambda r: r.get("publish_date", ""), reverse=True)
print(f"Clean records: {len(clean)}")

# JSONL
with open(f"{DATA}/chinatax_cases.jsonl", "w", encoding="utf-8") as f:
    for r in clean:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# JSON
with open(f"{DATA}/chinatax_cases.json", "w", encoding="utf-8") as f:
    json.dump(clean, f, ensure_ascii=False, indent=2)

# CSV
fields = ["article_id", "title", "url", "publish_date", "source", "content_text"]
with open(f"{DATA}/chinatax_cases.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in clean:
        w.writerow({k: r.get(k, "") for k in fields})

# Final verify
import hashlib
idx = json.load(open(f"{DATA}/chinatax_cases_index.json", encoding="utf-8"))
need = set(a["article_id"] for a in idx)
have = set(r["article_id"] for r in clean)
missing = need - have
extra = have - need
empty = sum(1 for r in clean if not r.get("content_text", "").strip())

print(f"\n{'='*50}")
print(f"  Index:      {len(idx)}")
print(f"  Articles:   {len(clean)}")
print(f"  Missing:    {len(missing)}")
print(f"  Extra:      {len(extra)}")
print(f"  Empty content: {empty}")
print(f"{'='*50}")

if missing:
    print(f"  ❌ MISSING: {list(missing)[:10]}")
else:
    print(f"  ✅ ALL {len(need)} ARTICLES PRESENT")

# Size check
for ext in ["jsonl", "json", "csv"]:
    path = f"{DATA}/chinatax_cases.{ext}"
    mb = __import__("os").path.getsize(path) / 1024 / 1024
    print(f"  📄 {ext}: {mb:.2f} MB")
