import gzip, json, argparse

def load_reviews(path, limit=None):
    revs = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            revs.append(r)
            if limit and len(revs) >= limit:
                break
    return revs

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=3)
    args = ap.parse_args()
    revs = load_reviews("data/Gift_Cards.jsonl.gz", args.limit)
    for r in revs:
        print("keys:", sorted(r.keys()))
        print("rating:", r.get("rating"), "| verified:", r.get("verified_purchase"),
              "| helpful:", r.get("helpful_vote"), "| ts:", r.get("timestamp"))
        print("title:", repr(r.get("title")))
        print("text:", repr(r.get("text")))
        print("---")
    # total count
    total = 0
    with gzip.open("data/Gift_Cards.jsonl.gz", "rt", encoding="utf-8") as f:
        total = sum(1 for _ in f)
    print("TOTAL REVIEWS:", total)
