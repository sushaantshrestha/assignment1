"""Shared data helpers: review loading, "correct answer from rating" rules, and
the NRC word-list emotion scorer."""
import gzip
import json
import re
from collections import Counter

from config import DATA_PATH, NRC_PATH, NRC_EMOTIONS, NRC_EMOTIONS_SET


def iter_reviews(path=DATA_PATH):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def load_reviews(path=DATA_PATH):
    return list(iter_reviews(path))


def star_to_2class(rating):
    """Two-class correct answer from the rating: >=4 positive, else negative."""
    return "POSITIVE" if rating >= 4 else "NEGATIVE"


def star_to_3class(rating):
    """Three-class correct answer: 4-5 positive, 3 neutral, 1-2 negative."""
    if rating >= 4:
        return "POSITIVE"
    if rating == 3:
        return "NEUTRAL"
    return "NEGATIVE"


# ---------------------------------------------------------------------------
# NRC word list
# ---------------------------------------------------------------------------
_WORD_RE = re.compile(r"[a-zA-Z']+")


def load_nrc(path=NRC_PATH):
    """Return {word: set(emotions)} considering only the 8 core emotions."""
    lex = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            term, emotion, flag = parts
            if emotion not in NRC_EMOTIONS_SET:
                continue
            if flag == "1":
                lex.setdefault(term.lower(), set()).add(emotion)
    return lex


def tokenize(text):
    if not text:
        return []
    return [w.lower().strip("'") for w in _WORD_RE.findall(text)]


def word_emotion_scores(text, lexicon=None):
    """Count word->emotion associations across a review. 0..1 per NRC term."""
    if lexicon is None:
        lexicon = load_nrc()
    counts = Counter()
    for w in tokenize(text):
        for emo in lexicon.get(w, ()):
            counts[emo] += 1
    return counts


def word_list_emotion(text, lexicon=None):
    """Primary emotion from the word list = highest association count, with a
    deterministic tie-break (order in NRC_EMOTIONS) so results are reproducible.
    Returns "none" when no NRC words are present."""
    counts = word_emotion_scores(text, lexicon)
    if not counts:
        return "none"
    best_emo = None
    best_n = -1
    for emo in NRC_EMOTIONS:  # deterministic order breaks ties
        n = counts.get(emo, 0)
        if n > best_n:
            best_n = n
            best_emo = emo
    return best_emo


if __name__ == "__main__":
    lex = load_nrc()
    print("NRC terms (with >=1 core emotion):", len(lex))
    for txt in ["I am so happy and excited about this!",
                "This product made me angry and disgusted.",
                "Just received, nothing special."]:
        print(repr(txt), "->", word_list_emotion(txt, lex))
