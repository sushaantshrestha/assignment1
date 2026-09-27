# Amazon Gift-Card Review Classifier

I built a sentiment and emotion classifier for **Amazon Reviews '23** *"Gift Cards"* reviews.
The model reads each review and says whether it is **positive**, **neutral**, or **negative**,
and which **emotion** it mostly shows. I then check the model's answer against the review's
star rating, and show everything in a dashboard that runs on its own, with no server.

![Dashboard (dark theme)](assets/dashboard-dark.png)

> **How to read this report:** each section maps to one step in the assignment, and every
> number here comes from the saved files in `output/`. If you re-run the scripts you get the
> same numbers, because I used a fixed seed (`2026`) and fixed model settings.

---

## 1. What I built

| Piece | File |
|---|---|
| The reusable prompt | `prompt.txt` |
| The scoring script (runs the LLM, adds the word-list emotion, checks vs. rating) | `scripts/run_classify.py` |
| The word-list emotion script (NRC lexicon) | `scripts/model.py` |
| The dashboard generator (one self-contained HTML page) | `scripts/make_dashboard.py` |
| Raw saved output of the balanced run | `output/classify_3class_balanced.json` |
| The final dashboard (open this file) | `dashboard/index.html` |

The prompt (`prompt.txt`) takes a review's **title and body** and asks the model to return one
JSON object: `{"sentiment": "...", "emotion": "...", "confidence": ...}`. I reuse the same
prompt for the two-class and the three-class tasks. The model **never sees the rating** — the
rating is only used afterwards to work out the "correct answer".

* **Data source:** [Amazon Reviews '23](https://amazon-reviews-2023.github.io) — the Amazon
  2023 review dataset from the McAuley Lab at UC San Diego. I used the Gift Cards category
  (`Gift_Cards.jsonl.gz`,
  [direct download](https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Gift_Cards.jsonl.gz)),
  which has **152,410 reviews**. For the word-list emotion taker I used the NRC emotion
  lexicon v0.92 (Mohammad & Turney, 2010).
* **Model:** an OpenAI-compatible endpoint (`DeepSeek-V4-Flash-0731`) run by a vLLM server,
  called from Python.

**What I kept from each review.** Each review has fields besides the title and text. I kept
`verified_purchase` (did the buyer actually buy it?), `helpful_vote` (how many people found
it helpful), `asin` (which product), and `timestamp`. I don't use them in the scoring itself,
but they help me explain odd reviews and would let me filter or compare later (for example,
whether unverified buyers write harsher reviews).

---

## 2. How I did it, step by step

### Step 1 · A structured prompt
`prompt.txt` asks the model to label a review **POSITIVE** or **NEGATIVE** and to answer as
clean JSON that a program can read. I decided the edge cases in the prompt: when the title and
the body disagree, the **body wins**; and short, angry reviews ("DO NOT BUY", "Love it!") are
judged on their own tone. I ran a quick spot-check on 6 clearly good and clearly bad reviews —
the model got all 6 right.

### Step 2 · A 100-row batch, checked against the rating
I scored the first 100 usable reviews and compared the model against the rule **≥4 stars →
POSITIVE, otherwise NEGATIVE**:

> **98/100 = 98% agreement.** Per class: POSITIVE 92/93 ≈ 99%, NEGATIVE 6/7 ≈ 86%.

**Why this number is misleading:** the sample is 93% positive, so a model that *always* says
POSITIVE would score 93%. The model's real edge over that easy baseline is only **+5 points**.

### Steps 3–4 · Dashboard + interactive filtering
`dashboard/index.html` is one self-contained file — it works offline with no server or
network. It shows headline numbers, agreement vs. baseline, per-class accuracy, a confusion
heatmap, star and class distributions, and emotion distributions. It has three color themes
(dark, light, sepia) that anyone can recolor by editing CSS variables. The review table can be
filtered — **all / correct / mismatched**, by class, by emotion, or by search — with a live
"Showing X of Y" count. Everything renders from the saved JSON, so what you see on the page is
what was recorded. I also verified the page in a real browser: no bars collapse, no console
errors.

### Step 5 · Two independent emotion takers
Each review gets a primary emotion **two different ways**, and I keep both:
1. **The LLM** — the same prompt also returns a primary emotion from the 8 NRC emotions.
2. **The word list (NRC)** — `scripts/model.py` counts the review's words against the NRC
   lexicon (anger, anticipation, disgust, fear, joy, sadness, surprise, trust), adds up the
   scores per emotion, and picks the highest (ties are broken in a fixed order; if no emotion
   words appear, it says `none`). No model calls needed.

### Step 6 · Three classes with balanced sampling (the main run)
I switched to the full three-class split and carried it through the answer rule, the prompt,
and the dashboard:

| Rating | Correct answer |
|---|---|
| 4–5 | **POSITIVE** |
| 3 | **NEUTRAL** |
| 1–2 | **NEGATIVE** |

Reading the first rows in order would give almost no 3-star reviews, so instead I pulled a
**balanced sample of about 50 per class from the whole file**, using `random.Random(seed=2026)`
— the same set appears every run.

### Step 7 · Descriptive and prediction charts
The dashboard shows the star-rating distribution, what the "correct answer" looks like vs.
what the model predicted for each class, and how often each class was answered right — so a
reader can see the failures without digging. I checked the charts in a real browser to make
sure tiny bars don't collapse (see the bugs section below).

---

## 3. Results — with evidence

### Headline, both runs (numbers read straight from the saved output)

| Run | Reviews | Agreement | Majority-class baseline | Edge over baseline |
|---|---|---|---|---|
| Imbalanced, 2-class (first 100) | 100 | **98.0%** | 93.0% | +5.0 pts |
| Balanced, 3-class (seed 2026) | 150 | **70.7%** | 33.3% | +37.3 pts |

### Why the lopsided run looked so accurate (Q1)

The data is extremely skewed. Across all 152,410 reviews: **88.5% are 4–5 star (POSITIVE),
9.3% are 1–2 star (NEGATIVE), and only 2.2% are 3-star (NEUTRAL)**. The first 100 reviews in
file order look exactly like that: 93 positive, 7 negative. So an agreement of 98% mostly just
shows the model agreeing on the easy, common class. The balanced run removes that illusion.
With about 50 of each class, the "always guess the most common class" baseline drops to
**33.3%**, and the model's 70.7% is a real **+37.3-point** edge. Balancing didn't just change
the headline number — it changed the story from "near-perfect" to "good, but with real
mistakes".

### Where the mistakes go — the confusion matrix (Q2)

Balanced 3-class run — **true class on the left, predicted across the top**:

| true \ predicted | POSITIVE | NEUTRAL | NEGATIVE |
|---|---|---|---|
| **POSITIVE** (n=50) | 44 | 6 | 0 |
| **NEUTRAL** (n=50) | 5 | 12 | 33 |
| **NEGATIVE** (n=50) | 0 | 0 | 50 |

Per-class accuracy: **NEGATIVE 50/50 = 100%, POSITIVE 44/50 = 88%, NEUTRAL 12/50 = 24%.**

The mistakes go almost one way: **33 of the 50 neutral (★★★) reviews were called NEGATIVE.**
The 3-star class does not really get its own label — it mostly collapses into NEGATIVE. When I
read those reviews, the reason is clear: a sincere 3-star review is usually written around a
complaint ("Needs More Work", "Tricky Checkout", "Envelopes don't fit"), so the model follows
the *tone of the words* even though the rating is only mildly negative. The opposite mistake —
calling a NEGATIVE review neutral or positive — basically never happens (0 each). A smaller
flow, POSITIVE → NEUTRAL (6/50), comes from very short positive reviews ("It's a gift card,
there is nothing else to say", "It works") that read as flat.

### LLM emotions vs. word-list emotions (Q3)

On the balanced run the two takers agree on only **19/150 = 12.7%** of reviews. They diverge
for a simple reason: they work completely differently.

* **The word list** counts words literally and takes the most common emotion. Gift-card
  reviews are full of words that the lexicon links to **anticipation** (*gift, easy, special,
  value, hope, arrive*), so `anticipation` wins 75 of 150 times. It cannot tell that "easy to
  use" is praise or that "I wish I knew about it earlier" is mild regret — it just counts
  words.
* **The LLM** reads the whole review and picks one overall emotion. So it lands on **anger**
  for the many complaint-driven neutral reviews (74 of 150) and **joy** for praise (42), and
  it says **none** for 18 flat reviews.

In short: the word list is a literal vote counter that over-uses anticipation and misses
context; the LLM understands context but is limited to eight coarse labels and can over-weight
one tone. They agree when the emotion is obvious and carried by clear words (like a plainly
angry short review), and disagree on everything contextual.

### Bugs and issues I hit along the way (Q4)

1. **The model's hidden "thinking" was eating the answer.** The endpoint is a reasoning model
   that thinks before it answers. With a small token limit, the thinking used up the whole
   budget and the JSON answer came back empty or cut off. I fixed it by giving the model more
   tokens and asking the endpoint for JSON output (`response_format={"type":"json_object"}`).
2. **Double braces in my prompt.** I first wrote the prompt with `format()`-style `{{ }}`
   braces but filled it in with `.replace()`, so the model saw `{{"sentiment"…}}` and copied
   it back. I switched the template to single braces.
3. **Charts with zero-height bars.** The first emotion chart drew zero-count columns at height
   0, which looked broken. I checked in a headless browser that those were genuinely
   zero-count emotions, then gave empty columns a faint stub so the axis still looks intact.
4. **The 2-class rule is unfair to 3-star reviews.** In the two-class step, a sincere 3-star
   review like "Very easy to use. I wish I knew about it earlier" counts as *NEGATIVE* (because
   the rule is ≥4) even though it reads positive. That artifact pushed me to the three-class
   step.
5. **Machine/setup friction.** The browser-automation tool needed a permission I couldn't get
   on this machine, so I installed a self-contained headless Chromium (Playwright) to verify
   the dashboard and take screenshots.
6. **A false alarm in my own check.** My early browser check counted the "no matches" message
   row as a real table row, so a correct "0 rows" filter looked like a bug. The dashboard was
   fine; the check was counting the wrong thing.

---

## 4. How to reproduce

All the numbers are stored in `output/`. To reproduce:

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

The API key is read from the `MBAX_API_KEY` environment variable **only** — the repository
never contains a credential. `MBAX_BASE_URL` and `MBAX_MODEL` default to the course endpoint
used for this run (`http://dobolyi.com:9000/v1` / `DeepSeek-V4-Flash-0731`). The seed (2026)
and temperature (0.0) are fixed, so running again gives the same answers.

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

*How I worked on this:* I built this project with an AI agent — it wrote the code, ran the
analysis, and drafted this report. Before submitting, I went through the report myself: I
re-checked every number against the saved files in `output/`, looked at the confusion matrix
and the mismatched reviews directly, and rewrote the explanations here in my own words so they
reflect what I actually did and learned.

*Data citation:* Hou, Yupeng; Li, Jiacheng; He, Zhankui; Yan, An; Chen, Xiusi; McAuley, Julian.
"Bridging Language and Items for Retrieval and Recommendation." arXiv:2403.03952 (2024) — the
Amazon Reviews '23 dataset, hosted by the McAuley Lab at UC San Diego:
https://amazon-reviews-2023.github.io
