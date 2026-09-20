"""Step 1 spot check: classify a small set of hand-picked obvious reviews and print
the model's answer so we can eyeball agreement with the expected tone."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import classify, TWO_CLASS

# (title, text, expected)
CASES = [
    ("Great gift", "Having Amazon money is always good.", "POSITIVE"),
    ("perfect gift", "They are thrilled and excited to have a bit of a spree.", "POSITIVE"),
    ("DO NOT BUY", "Card was never delivered and they refused to refund me. Terrible.", "NEGATIVE"),
    ("Scam", "This gift card came with a zero balance and no way to redeem it.", "NEGATIVE"),
    ("Disappointed", "Not what I expected, wish I got something else.", "NEGATIVE"),
    ("Love it", "Wish I had found this sooner, everyone should get one.", "POSITIVE"),
]

print(f"{'title':<16}{'expected':<12}{'model':<12}{'emotion':<12}{'conf':<6}")
print("-" * 70)
all_ok = True
for title, text, expected in CASES:
    res = classify(title, text, TWO_CLASS)
    ok = res["sentiment"] == expected
    all_ok = all_ok and ok
    print(f"{title[:15]:<16}{expected:<12}{str(res['sentiment']):<12}"
          f"{str(res['emotion']):<12}{str(res['confidence']):<6}{'OK' if ok else 'MISS'}")
    print("   raw:", (res.get("raw") or "")[:120].replace("\n", " "))
print("\nALL CORRECT" if all_ok else "\nSOME MISSED")
