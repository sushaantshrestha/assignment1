import json, sys, re

# Pull the embedded RUNS data straight out of the built HTML (the same JSON the
# page renders from) so the check is against the actual deliverable.
html = open("dashboard/index.html", encoding="utf-8").read()
m = re.search(r"const RUNS = (\{.*?\});\nlet current", html, re.S)
assert m, "RUNS not found in HTML"
from json import loads
runs = loads(m.group(1))
assert len(runs) == 1, list(runs)
run = list(runs.values())[0]
rows = run["rows"]

def matches(r, fcorrect, fclass, femo, fsearch):
    ok = r["pred"] == r["correct"]
    if fcorrect == "correct" and not ok: return False
    if fcorrect == "mismatch" and ok: return False
    if fclass != "all" and r["correct"] != fclass: return False
    if femo != "all" and r["llm_emotion"] != femo and r["nrc_emotion"] != femo: return False
    if fsearch and not ((r["title"] or "") + " " + (r["text"] or "")).lower().count(fsearch): return False
    return True

def count(fc="all", fl="all", fe="all", fs=""):
    return sum(1 for r in rows if matches(r, fc, fl, fe, fs))

print("TOTAL rows:", len(rows))
print("correct:", count("correct"), "| mismatched:", count("mismatch"))
print("search 'gift':", count(fs="gift"))
print("class NEGATIVE:", count(fl="NEGATIVE"))
# Combined: mismatched AND negative
combo = sum(1 for r in rows if matches(r, "mismatch", "NEGATIVE", "all", ""))
print("mismatch AND class NEGATIVE:", combo)
# Show the actual mismatched rows to cross-check against the UI
mm = [r for r in rows if r["pred"] != r["correct"]]
print("\nMismatched rows (%d):" % len(mm))
for r in mm:
    print("  rating=%s correct=%s pred=%s | %s" % (r["rating"], r["correct"], r["pred"], r["title"]))

# Sanity: agreement equals 98% of the run meta
agree = sum(1 for r in rows if r["pred"] == r["correct"])
print("\nagreement:", agree, "/", len(rows))
print("meta.agreement:", run["meta"]["agreement"])
