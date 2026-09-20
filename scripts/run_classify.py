"""Run a classification batch: sample reviews, ask the LLM for sentiment + emotion,
derive the NRC word-list emotion, and compare against the rating-based answer.

Modes
-----
--class-mode 2  two-class (POSITIVE/NEGATIVE), correct = rating>=4
--class-mode 3  three-class (POSITIVE/NEUTRAL/NEGATIVE), correct = {4-5,3,1-2}

Sampling
--------
--sample first      first N reviews (imbalanced stream; mirrors file order)
--sample balanced   ~N per class pulled from the WHOLE file with a fixed seed

Only reviews with a non-empty title AND body are kept. The model never sees the
rating. Every number the report / dashboard quotes comes from the saved JSON.
"""
import argparse, sys, os, json, random, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import SEED, NRC_EMOTIONS
from model import (iter_reviews, star_to_2class, star_to_3class,
                   load_nrc, word_list_emotion, word_emotion_scores)
from llm import classify, TWO_CLASS, THREE_CLASS

# Required sub-fields kept from each raw review.
KEEP = ["asin", "parent_asin", "user_id", "verified_purchase", "helpful_vote",
        "timestamp"]


def row_is_usable(r):
    return bool(r.get("title", "").strip()) and bool(r.get("text", "").strip())


def sample_reviews(mode, n, seed=SEED):
    """Return (rows, how) where how explains the sampling for provenance."""
    usable = [r for r in iter_reviews() if row_is_usable(r)]
    if mode == "first":
        how = f"first {n} usable reviews in file order"
        return usable[:n], how
    # balanced sampling per class
    rng = random.Random(seed)
    by_class = {}
    for r in usable:
        c = star_to_3class(r["rating"])
        by_class.setdefault(c, []).append(r)
    chosen = []
    for c in ["POSITIVE", "NEUTRAL", "NEGATIVE"]:
        pool = by_class.get(c, [])
        sampled = rng.sample(pool, min(n, len(pool)))
        chosen.extend(sampled)
    rng.shuffle(chosen)  # interleave so the LLM can't infer from neighbors
    how = (f"balanced {len(chosen)} rows (~{n}/class) sampled with seed={seed} "
           f"from the whole file")
    return chosen, how


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class-mode", type=int, choices=[2, 3], required=True)
    ap.add_argument("--sample", choices=["first", "balanced"], required=True)
    ap.add_argument("--n", type=int, default=50, help="count (per class if balanced)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    labels = TWO_CLASS if args.class_mode == 2 else THREE_CLASS
    correct_fn = star_to_2class if args.class_mode == 2 else star_to_3class
    lexicon = load_nrc()

    reviews, how = sample_reviews(args.sample, args.n, args.seed)
    print(f"Classifying {len(reviews)} reviews | labels={labels} | {how}")

    rows = []
    start = time.time()
    for i, r in enumerate(reviews, 1):
        title, text = r["title"], r["text"]
        res = classify(title, text, labels)
        correct = correct_fn(r["rating"])
        nrc_scores = word_emotion_scores(text, lexicon)
        row = {
            "idx": i - 1,
            "rating": r["rating"],
            "correct": correct,
            "pred": res.get("sentiment"),
            "llm_emotion": res.get("emotion"),
            "llm_conf": res.get("confidence"),
            "llm_error": res.get("error"),
            "nrc_scores": dict(nrc_scores),
            "nrc_emotion": word_list_emotion(text, lexicon),
            "title": title,
            "text": text,
        }
        for k in KEEP:
            row[k] = r.get(k)
        rows.append(row)
        if i % 10 == 0 or i == len(reviews):
            print(f"  {i}/{len(reviews)} done ({time.time()-start:.0f}s)", flush=True)

    n_agree = sum(1 for r in rows if r["pred"] == r["correct"])
    meta = {
        "dataset": "Amazon Reviews '23 Gift_Cards",
        "model": "openai-compatible DeepSeek-V4-Flash-0731",
        "class_mode": args.class_mode,
        "labels": labels,
        "correct_rule": ("rating>=4 -> POSITIVE else NEGATIVE" if args.class_mode == 2
                         else "4-5 POSITIVE, 3 NEUTRAL, 1-2 NEGATIVE"),
        "sample": how,
        "seed": args.seed,
        "n_rows": len(rows),
        "n_agree": n_agree,
        "agreement": round(n_agree / len(rows), 4) if rows else None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out = {"meta": meta, "rows": rows}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(rows)} rows -> {args.out}")
    print(f"Agreement with rating: {n_agree}/{len(rows)} = {meta['agreement']:.2%}")


if __name__ == "__main__":
    main()
