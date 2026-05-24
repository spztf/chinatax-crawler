"""Sync JSONL to JSON."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

data_dir = Path(__file__).parent / "data"
jsonl = data_dir / "chinatax_cases.jsonl"
jsonf = data_dir / "chinatax_cases.json"

records = []
with open(jsonl, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

records.sort(key=lambda r: r.get("publish_date", ""), reverse=True)
with open(jsonf, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
print(f"Synced {len(records)} records to JSON")
