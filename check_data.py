"""检查已有数据状态"""
import json, pickle, sys
from pathlib import Path

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8')

data_dir = Path(__file__).parent / "data"

# 各文件大小
for f in sorted(data_dir.glob("*.json*")):
    size_mb = f.stat().st_size / 1024 / 1024
    print(f"  {f.name}: {size_mb:.2f} MB")

# 主数据
main = data_dir / "chinatax_cases.json"
if main.exists():
    with open(main, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    print(f"\n[*] 文章总数: {len(d)}")
    if d:
        print(f"  第1条: {d[0]['title'][:80]}")
        print(f"  最后1条: {d[-1]['title'][:80]}")
        dates = [a.get('publish_date', '') for a in d if a.get('publish_date')]
        if dates:
            print(f"  日期范围: {min(dates)} ~ {max(dates)}")
        chars = sum(len(a.get('content_text', '')) for a in d)
        print(f"  正文总字数: {chars:,}")

# 索引
idx = data_dir / "chinatax_cases_index.json"
if idx.exists():
    with open(idx, "r", encoding="utf-8") as fh:
        idxd = json.load(fh)
    print(f"\n[*] 索引条目: {len(idxd)}")

# 检查点
cp = data_dir / "checkpoint" / "chinatax_cases_checkpoint.pkl"
if cp.exists():
    with open(cp, "rb") as fh:
        cpd = pickle.load(fh)
    print(f"\n[*] 检查点完成数: {len(cpd)}")
else:
    print("\n[*] 无检查点文件")

# CSV
csv = data_dir / "chinatax_cases.csv"
if csv.exists():
    print(f"\n[*] CSV: {csv.stat().st_size / 1024:.1f} KB")
