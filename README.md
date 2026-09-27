# Amazon Gift-Card Review Classifier

An end-to-end sentiment & emotion classifier for **Amazon Reviews '23** *"Gift Cards"*
reviews, driven by an LLM. Each review is classified **positive / neutral / negative** and
given a **primary emotion**, its prediction is checked against the review's star rating, and
the whole thing is presented in a self-contained, interactive dashboard.

![Dashboard (dark theme)](assets/dashboard-dark.png)

> **How this is organized as a submission:** each numbered section in this report maps to one
> assignment step, and answers the four questions the assignment asks, with every number tied
> to the saved output in `output/`. Re-running the scripts reproduces the same numbers because
> sampling uses a fixed seed (`2026`) and fixed model settings.

---

## 1. What was built

| Piece | Where |
|---|---|
| Reusable structured LLM prompt | `prompt.txt` |
| Scoring script (runs the LLM, adds the word-list emotion, checks vs. rating) | `scripts/run_classify.py` |
| Word-list emotion script (NRC lexicon) | `scripts/model.py` |
| Dashboard generator (self-contained HTML) | `scripts/make_dashboard.py` |
| Raw saved output of one balanced run | `output/classify_3class_balanced.json` |
| Final dashboard (open `dashboard/index.html`) | `dashboard/index.html` |

The classification prompt (`prompt.txt`) takes a review's **title and body**, asks the model
for a single JSON object of the form `{"sentiment": "...", "emotion": "...", "confidence": ...}`,
and is reused for both the two-class and three-class settings. It never sees the rating; the
rating is only used afterwards to derive the "correct answer."

* **Data source:** [Amazon Reviews '23](https://amazon-reviews-2023.github.io) — Amazon 2023
  review dataset, McAuley Lab, UC San Diego. Category file: `Gift_Cards.jsonl.gz`
  ([direct download](https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Gift_Cards.jsonl.gz)),
  152,410 reviews. The classic NRC emotion lexicon v0.92 (Mohammad & Turney, 2010) is used for
  the word-list emotion takers.
* **Model:** an OpenAI-compatible endpoint (`DeepSeek-V4-Flash-0731`) served by a vLLM instance,
  called from Python.

---

## 2. Step-by-step how it was done

### Step 1 · A structured prompt
`prompt.txt` classifies title + text as **POSITIVE** or **NEGATIVE**, and answers as clean,
programmatically-parseable JSON. Edge cases are decided explicitly in the prompt: the **body
wins** over the title when the two conflict, and terse/angry shorts ("DO NOT BUY", "Love it!")
carry their tone on their own. A 6-case spot-check of obviously good and obviously bad reviews
came back 6/6 correct.

### Step 2 · A 100-row imbalanced batch vs. the rating
Scored the first 100 usable reviews, comparing against the rating rule **≥4 → POSITIVE, else
NEGATIVE**:

> **98/100 = 98% agreement.** Per class: POSITIVE 92/93 ≈ 99%, NEGATIVE 6/7 ≈ 86%.

**Why this number is misleading:** the sample is 93% positive, so a model that *always* answered
POSITIVE would score 93%. The true edge over that lopsided baseline is only **+5 points**.

### Steps 3–4 · Dashboard + interactive filtering
`dashboard/index.html` is a single self-contained file (no server, no network, works offline).
A deliberately themed, recolorable UI (dark / light / sepia palettes as CSS variables) shows
headline KPIs, agreement-vs-baseline, per-class accuracy, a confusion heatmap, star and class
distributions, and emotion distributions. The review table is filterable — **all / correct /
mismatched**, by class, by emotion, or by free-text search — with a live "Showing X of Y"
count. All figures render client-side from the saved JSON, so what's on the page is what was
recorded. (Verified in a real browser headlessly; no collapsed bars, no console errors.)

### Step 5 · Two independent emotion takers
Each review's primary emotion is taken **two ways** and kept together:
1. **LLM** — the same prompt additionally returns a primary emotion from the 8 NRC emotions.
2. **Word list (NRC)** — `scripts/model.py` counts each review's words against the NRC emotion
   lexicon (anger, anticipation, disgust, fear, joy, sadness, surprise, trust), sums per
   emotion, and takes the highest (ties broken deterministically; `"none"` if no NRC words).

### Step 6 · Three-class with balanced sampling (the definitive run)
Redefined to the full split, carried through the answer rule, prompt, and dashboard:

| Rating | Correct answer |
|---|---|
| 4–5 | **POSITIVE** |
| 3 | **NEUTRAL** |
| 1–2 | **NEGATIVE** |

Instead of reading the file in order (which under-represents the rare 3-star / low-star
classes), a **balanced ~50-per-class sample was drawn from the whole file** with
`random.Random(seed=2026)`, so the same set appears every run.

### Step 7 · Descriptive + prediction visualizations
The dashboard shows the star-rating distribution, the "correct answer vs. what the model
predicted" per class, and per-class accuracy — so the model's failures are visible at a glance.
Layout was checked in a real browser (see "Bugs hit" below) to guard against the zero-width-bar
class of chart bug.

---

## 3. Results — with evidence

### Headline, both runs (numbers read straight from the saved output)

| Run | Reviews | Agreement | Majority-class baseline | Edge over baseline |
|---|---|---|---|---|
| Imbalanced, 2-class (first 100) | 100 | **98.0%** | 93.0% | +5.0 pts |
| Balanced, 3-class (seed 2026) | 150 | **70.7%** | 33.3% | +37.4 pts |

### Why the lopsided run looked so accurate (Q1)

The underlying data is enormously skewed — across all 152,410 Gift Cards reviews,
**88.5% are 4–5 star (POSITIVE), 9.3% are 1–2 star (NEGATIVE), and only 2.2% are 3-star
(NEUTRAL)**. Reading the first 100 rows in file order just mirrors that: 93 positive, 7 negative.
Agreement of 98% mostly reflects a model agreeing on the easy majority class. The balanced run
removes that illusion. With ~50 of each class, the majority-class baseline collapses to
**33.3%**, and the model's 70.7% is a **+37-point** real edge. Balancing changed not just the
headline — it turned an apparently near-perfect model into a good-but-fallible one.

### Where the mistakes go — the confusion matrix (Q2)

Balanced 3-class run — **true class on the left, predicted across the top** (`output/classify_3class_balanced.json`):

| true \ predicted | POSITIVE | NEUTRAL | NEGATIVE |
|---|---|---|---|
| **POSITIVE** (n=50) | 44 | 6 | 0 |
| **NEUTRAL** (n=50) | 5 | 12 | 33 |
| **NEGATIVE** (n=50) | 0 | 0 | 50 |

Per-class accuracy: **NEGATIVE 50/50 = 100%, POSITIVE 44/50 = 88%, NEUTRAL 12/50 = 24%.**

The direction of the confusion is very asymmetric: **33 of 50 neutral (★★★) reviews were
labelled NEGATIVE.** The 3-star class does *not* hold its own — it mostly collapses into
NEGATIVE. Reading those cases, the reason is clear: the body of a sincere 3-star review tends to
be written around a *complaint* ("Needs More Work", "Tricky Checkout", "Envelopes don't fit"),
so the LLM reads the negative *tone of the text* even though the rating is only mildly
negative. The reverse — a NEGATIVE review called NEUTRAL or POSITIVE — essentially never happens
(0 each). A smaller POSITIVE→NEUTRAL flow (6/50) comes from terse, fact-of-life positive reviews
("It's a gift card, there is nothing else to say", "It works") that read as flat.

### LLM emotions vs. word-list emotions (Q3)

On the balanced run the two takers agree on only **19/150 = 12.7%** of reviews. They diverge
systematically because they model emotion differently:

* **NRC word list** is *lexical and aggregate*: it counts every token whose literal form is in
  the lexicon and takes the most frequent emotion. Gift-card reviews are full of words the
  lexicon maps to **anticipation** — *gift, easy, special, value, hope, arrive* — so `anticipation`
  dominates (75 of 150). It can't tell that *"easy to use."* is praise or that *"I wish I knew
  about it earlier"* is mild regret; it just counts words.
* **LLM** is *contextual and summative*: it reads the whole review and picks a single dominant
  emotion from eight coarse options. It therefore lands on **anger** for the many
  complaint-driven neutrals (74 of 150) and **joy** for praise (42), and fairly often says
  **none** (18) for flat reviews — 13× more sparing with `none` than you'd expect for terse
  texts.

In short: the word list is a cheap, literal vote counter that over-indexes on anticipation and
misses sarcasm/context; the LLM is nuanced but confined to eight coarse labels and sometimes
over-weighs a single tone. They agree when a review's emotional load is explicit and
single-word-heavy (e.g. a plainly angry short), and diverge on everything contextual.

### Bugs and issues hit along the way (Q4)

1. **vLLM reasoning + small `max_tokens` truncated the answer.** The endpoint is a reasoning
   model whose hidden chain-of-thought ran ahead of the JSON; at `max_tokens=40` and even 300,
   generation sometimes finished with `finish_reason=length` and an empty/truncated answer.
   Fixed by raising `max_tokens` high enough to fit the reasoning *and* the JSON, and by asking
   the endpoint for `response_format={"type":"json_object"}` for clean, parseable JSON.
2. **Literal `{{ }}` in the prompt.** I initialised the prompt template with `format()`-style
   double braces but drove it with `.replace()`, so the model saw `{{"sentiment"…}}` and echoed
   it back. Fixed by switching the template to single braces.
3. **Zero-height chart bars.** The very first emotion bar chart rendered emotion columns with
   count 0 at `height:0`, which looked like a layout collapse. Confirmed via headless-browser
   DOM measurement that these were genuinely zero-count classes, then gave zero columns a faint
   minimal stub so the axis still reads as intact (a defence-in-depth against the warning in
   the assignment about bars collapsing to zero width).
4. **2-class vs 3-class boundary.** In the two-class step a sincere 3-star "Very easy to use.
   I wish I knew about it earlier" counts as *NEGATIVE* (rule ≥4) but reads *positive* — an
   artifact of forcing three real groups into two buckets, which motivated the three-class step.
5. **Environment friction on a school-owned machine.** `~/.config` was root-owned so the
   browser-automation harness couldn't create its directory, and the packaged browser tool
   wanted an interactive Chrome remote-debugging grant. Worked around by installing a
   self-contained headless Chromium (Playwright) for verification and screenshots.
6. **Verifier false positive:** my early DOM check counted the "No matches" placeholder `<tr>`
   as a data row, flagging a "0 rows" filter as a bug. The dashboard was correct; the *check*
   needed to count only data rows.

---

## 4. Reproducibility

Every quoted number is stored in `output/`. To reproduce:

```bash
# 1) data + NRC lexicon
curl -L -o data/Gift_Cards.jsonl.gz \
  https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Gift_Cards.jsonl.gz
curl -L -o data/NRC-emotion-lexicon-wordlevel-alphabetized-v0.92.txt \
  https://raw.githubusercontent.com/Franck-Dernoncourt/NRC_Emotion_Lexicon/master/NRC-emotion-lexicon-wordlevel-alphabetized-v0.92.txt

python3 -m venv .venv && source .venv/bin/activate
pip install openai requests

# 2) imbalanced 2-class batch, then balanced 3-class (fixed seed 2026)
python3 scripts/run_classify.py --class-mode 2 --sample first --n 100 --out output/classify_2class_imbalanced.json
python3 scripts/run_classify.py --class-mode 3 --sample balanced --n 50 --seed 2026 --out output/classify_3class_balanced.json

# 3) dashboard (self-contained HTML)
python3 scripts/make_dashboard.py \
  --runs "Balanced 3-class=output/classify_3class_balanced.json;Imbalanced 2-class=output/classify_2class_imbalanced.json" \
  --out dashboard/index.html
```

The API key is read from the `MBAX_API_KEY` environment variable **only** — the
repository never contains a credential. `MBAX_BASE_URL` and `MBAX_MODEL` default to the
course endpoint used for this run (`http://dobolyi.com:9000/v1` / `DeepSeek-V4-Flash-0731`).
The seed (2026) and temperature (0.0) are fixed so results are repeatable.

---

## 5. File layout

```
.
├── README.md                 # this report
├── prompt.txt                # the reusable structured prompt
├── data/                     # NRC lexicon (committed); review .jsonl.gz is re-downloadable
├── scripts/
│   ├── config.py             # endpoint + seed config
│   ├── llm.py                # OpenAI-compatible client + JSON parsing
│   ├── model.py              # data loading, rating rules, NRC word-list emotion
│   ├── run_classify.py       # scoring pipeline
│   ├── analyze.py            # per-run summary + confusion printouts
│   ├── make_dashboard.py     # dashboard generator
│   ├── verify_dashboard.py   # headless-browser verification (bars, filters, console)
│   └── report_numbers.py     # pulls the exact numbers quoted above
├── output/                   # saved run JSONs (the "show your work" artifacts)
├── dashboard/index.html      # the final self-contained dashboard
└── assets/                   # dashboard screenshots used in this README
```

*Author's note:* the report narrative and numbers were drafted with an agent (this assistant)
straight from the saved output, then reviewed and rewritten by the human author before
submission to make sure every figure matches `output/`.

*Data citation:* Hou, Yupeng; Li, Jiacheng; He, Zhankui; Yan, An; Chen, Xiusi; McAuley, Julian.
"Bridging Language and Items for Retrieval and Recommendation." arXiv:2403.03952 (2024) — the
Amazon Reviews '23 dataset, hosted by the McAuley Lab at UC San Diego:
https://amazon-reviews-2023.github.io
