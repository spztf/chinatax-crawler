"""从已有 JSONL 构建检查点，然后运行爬虫续抓"""
import json, pickle, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

data_dir = Path(__file__).parent / "data"
jsonl = data_dir / "chinatax_cases.jsonl"
cp_dir = data_dir / "checkpoint"
cp_file = cp_dir / "chinatax_cases_checkpoint.pkl"

# 从 JSONL 中提取已完成的 article_id
done = set()
if jsonl.exists():
    with open(jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rec = json.loads(line)
                    aid = rec.get("article_id", "")
                    if aid:
                        done.add(aid)
                except json.JSONDecodeError:
                    pass

print(f"JSONL 中已有 {len(done)} 条记录")

# 保存检查点
cp_dir.mkdir(parents=True, exist_ok=True)
with open(cp_file, "wb") as f:
    pickle.dump(done, f)
print(f"检查点已保存: {len(done)} 个 ID -> {cp_file}")
