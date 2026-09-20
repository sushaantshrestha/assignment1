import gzip, json, argparse
from collections import Counter

def iter_reviews(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)

def star_to_2class(r):
    return "POSITIVE" if r["rating"] >= 4 else "NEGATIVE"

def star_to_3class(r):
    r_ = r["rating"]
    if r_ >= 4: return "POSITIVE"
    if r_ == 3: return "NEUTRAL"
    return "NEGATIVE"

if __name__ == "__main__":
    stars = Counter(); hd = Counter(); vp = Counter(); c2 = Counter(); c3 = Counter()
    no_text = 0; total = 0
    for r in iter_reviews("data/Gift_Cards.jsonl.gz"):
        total += 1
        stars[r["rating"]] += 1
        hd[r["rating"]] += 1
        vp[r["verified_purchase"]] += 1
        c2[star_to_2class(r)] += 1
        c3[star_to_3class(r)] += 1
        if not (r.get("title") and r.get("text") and r["text"].strip()):
            no_text += 1
    print("TOTAL:", total)
    print("\nStar distribution:")
    for s in sorted(stars): print(f"  {s} star: {stars[s]:>7}  ({100*stars[s]/total:.2f}%)")
    print("\nTwo-class (rating>=4 pos):")
    for c in c2: print(f"  {c}: {c2[c]:>7} ({100*c2[c]/total:.2f}%)")
    print("\nThree-class:")
    for c in ["POSITIVE","NEUTRAL","NEGATIVE"]: print(f"  {c}: {c3[c]:>7} ({100*c3[c]/total:.2f}%)")
    print("\nVerified purchase:", dict(vp))
    print("Reviews missing title or text:", no_text)
