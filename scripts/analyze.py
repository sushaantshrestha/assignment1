"""Summarize a saved run: agreement, per-class accuracy, and confusion counts.
Usage: python3 scripts/analyze.py output/<file>.json"""
import sys, os, json
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

path = sys.argv[1] if len(sys.argv) > 1 else None
if not path:
    sys.exit("usage: analyze.py <run.json>")
data = json.load(open(path, encoding="utf-8"))
meta, rows = data["meta"], data["rows"]

# Overall
agree = sum(1 for r in rows if r["pred"] == r["correct"])
print(f"Run: {path}")
print(f"  {meta.get('sample')}")
print(f"  Overall agreement: {agree}/{len(rows)} = {agree/len(rows):.1%}")
n_none = sum(1 for r in rows if r["pred"] is None)
print(f"  LLM failures (no label): {n_none}")

# Class balance of the sample
cbal = Counter(r["correct"] for r in rows)
print(f"  Correct-class distribution: {dict(cbal)}")

# "Always predict majority" baseline
if cbal:
    top = cbal.most_common(1)[0][1]
    print(f"  Baseline (always predict most common class): {top/len(rows):.1%}")

# Per-class accuracy (correct label vs predicted)
print("\n  Per-class accuracy (rows whose correct=class, fraction predicted same):")
for cls in sorted(set(r["correct"] for r in rows)):
    sub = [r for r in rows if r["correct"] == cls]
    ok = sum(1 for r in sub if r["pred"] == cls)
    print(f"    {cls:<10} n={len(sub):<4} acc={ok/len(sub):.1%}" if sub else f"    {cls}: none")

# Confusion matrix (rows where pred != correct)
print("\n  Confusion (correct -> predicted), mismatches only:")
conf = Counter((r["correct"], r["pred"] or "NONE") for r in rows if r["pred"] != r["correct"])
for (c, p), n in sorted(conf.items(), key=lambda x: -x[1]):
    print(f"    {c} -> {p}: {n}")

# Mismatched rows detail
print("\n  Mismatched reviews:")
i = 0
for r in rows:
    if r["pred"] != r["correct"]:
        i += 1
        print(f"  [{i}] rating={r['rating']} correct={r['correct']} pred={r['pred']} "
              f"conf={r['llm_conf']}")
        print(f"      title: {r['title']}")
        print(f"      text : {r['text'][:150]}")
        print(f"      nrc_emotion={r['nrc_emotion']} llm_emotion={r['llm_emotion']}")
