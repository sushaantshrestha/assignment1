import json
from collections import Counter

def load(p):
    return json.load(open(p, encoding="utf-8"))

bal = load("output/classify_3class_balanced.json")
imb = load("output/classify_2class_imbalanced.json")

def agreement(run):
    return sum(1 for r in run["rows"] if r["pred"] == r["correct"])

def baseline_pct(run):
    cnt = Counter(r["correct"] for r in run["rows"])
    return max(cnt.values()) / len(run["rows"])

def confusion(run, classes):
    m = {a: {b: 0 for b in classes} for a in classes}
    for r in run["rows"]:
        m[r["correct"]][r["pred"] or "NONE"] = m[r["correct"]].get(r["pred"] or "NONE", 0) + 1
    return m

def per_class(run, classes):
    out = {}
    for c in classes:
        sub = [r for r in run["rows"] if r["correct"] == c]
        out[c] = (sum(1 for r in sub if r["pred"] == c), len(sub))
    return out

def emo_agree(run):
    a = sum(1 for r in run["rows"] if r["llm_emotion"] == r["nrc_emotion"])
    return a, len(run["rows"])

def nrc_top_counts(run):
    return Counter(r["nrc_emotion"] for r in run["rows"])

def llm_top_counts(run):
    return Counter(r["llm_emotion"] for r in run["rows"])

print("=" * 60)
print("IMBALANCED 2-CLASS (first 100)")
a = agreement(imb); n = len(imb["rows"])
print(f"  agreement {a}/{n} = {a/n:.1%}   baseline(all-positive) = {baseline_pct(imb):.1%}")
print(f"  per-class: {per_class(imb, ['POSITIVE','NEGATIVE'])}")
print(f"  emotion agreement LLMvsNRC: {emo_agree(imb)[0]}/{emo_agree(imb)[1]} = {emo_agree(imb)[0]/emo_agree(imb)[1]:.1%}")
print(f"  LLM top emotions: {dict(llm_top_counts(imb))}")
print(f"  NRC top emotions:  {dict(nrc_top_counts(imb))}")

print("=" * 60)
print("BALANCED 3-CLASS (~50/class, seed 2026)")
a = agreement(bal); n = len(bal["rows"])
print(f"  agreement {a}/{n} = {a/n:.1%}   baseline(all-majority) = {baseline_pct(bal):.1%}")
print(f"  per-class: {per_class(bal, ['POSITIVE','NEUTRAL','NEGATIVE'])}")
m = confusion(bal, ['POSITIVE','NEUTRAL','NEGATIVE'])
print("  confusion (correct x pred):")
for c in ['POSITIVE','NEUTRAL','NEGATIVE']:
    print(f"    {c:<9}", {k: v for k, v in m[c].items()})
print(f"  emotion agreement LLMvsNRC: {emo_agree(bal)[0]}/{emo_agree(bal)[1]} = {emo_agree(bal)[0]/emo_agree(bal)[1]:.1%}")
print(f"  LLM top emotions: {dict(llm_top_counts(bal).most_common())}")
print(f"  NRC top emotions:  {dict(nrc_top_counts(bal).most_common())}")

# neutral reviews predicted negative; count and a sample
neutral_neg = [r for r in bal["rows"] if r["correct"]=='NEUTRAL' and r['pred']=='NEGATIVE']
print(f"\n  NEUTRAL-rating reviews the model called NEGATIVE: {len(neutral_neg)}/{len([r for r in bal['rows'] if r['correct']=='NEUTRAL'])}")
