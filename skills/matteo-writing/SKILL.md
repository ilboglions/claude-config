---
name: matteo-writing
description: Apply Matteo's academic writing style when drafting or editing text. Use when writing LaTeX prose, paper sections, abstracts, rebuttals, or any academic text for Matteo.
---

# Matteo Writing Style Guide

Use this guide whenever writing or editing academic text for Matteo. Match these
patterns. When in doubt, prefer these conventions over generic academic writing
defaults.

**Evidence base:** derived from LACUNA (COLM 2026) — abstract, introduction, and
conclusion. Extend this file as more papers are written; a pattern seen in one
paper is a weaker signal than one seen in three.

---

## HARD RULES

### Always "we", never "I"
Academic "we" throughout, including in single-author text and in rebuttals.

### No contractions
Write "do not", "cannot", "it is". Never "don't", "can't", "it's".

### No exclamation marks
Academic register throughout.

### Em-dashes ARE used, but only for one job
Unlike many style guides, do not avoid em-dashes. Matteo uses them specifically
to attach an *e.g.* or *i.e.* clarification to the term just introduced, with no
surrounding spaces:

> "...but also because of second-order privacy risks—e.g., facilitating the memorization of more PII later in the training pipeline."

> "...focused on localization precision—i.e., the extent to which unlearning targets the weights responsible for knowledge storage."

Do not use em-dashes for general parenthetical asides; use commas or parentheses
for those.

### Introduce every acronym in parentheses on first use
> "personally identifiable information (PII)"
> "state-of-the-art (SOTA)"

### Italicize key technical terms at the moment of definition
> "...not informative about true *knowledge erasure* from a model's parameters."
> "...demonstrating it was never truly erased but merely *obfuscated*."

Reserve italics for this. Do not use bold for emphasis in body text.

---

## THE SIGNATURE MOVE: problem → gap → "To bridge this gap, we introduce X"

This exact arc appears in both the abstract and the introduction of LACUNA. It is
the most recognizable pattern in the writing. Use it to open any paper or section
that presents an artifact:

1. State what the field does today (neutral, factual).
2. Name the shortcoming with "However," or "These benchmarks, however,".
3. Close the gap explicitly: **"To bridge this gap, we introduce X: <appositive gloss>"**

> "However, existing benchmarks evaluate unlearning solely at the output level, leaving open the question of whether unlearning truly erases knowledge from a model's parameters or merely obfuscates it, a concern reinforced by the success of resurfacing attacks. To bridge this gap, we introduce LACUNA: the first unlearning testbed with ground-truth parameter-level localization."

Note the colon-plus-appositive after the name. The artifact is named, then
immediately glossed in a noun phrase, not a new sentence.

---

## CONTRIBUTION LISTS

Introduce with "Concretely, we make the following contributions:" then a numbered
list. Every item starts with "We" plus a strong verb (present, release, employ,
introduce, show, analyze):

> 1. We present a scalable approach to inject PII into dedicated parameters...
> 2. We release Lacuna, a novel unlearning testbed that includes...
> 3. We employ Lacuna to assess unlearning methods and show that...
> 4. We introduce and analyze a highly precise unlearning oracle, demonstrating that...

Items are full sentences, not fragments. Longer items chain a result onto the
contribution with "and show that..." or "demonstrating that...".

---

## TRANSITIONS & CONNECTIVES

| Function | Words used |
|---|---|
| Contrast | "However," / "These X, however," / "In contrast," / "Instead," |
| Concession | "At the same time," / "despite strong output-level performance," |
| Reinforcement | "In fact," / "Notably," |
| Specifics follow | "Concretely," |
| Summation | "Overall," |
| Consequence | "Therefore," / "This demonstrates that" |
| Enumerating directions | "Firstly, ... Secondly, ..." |

Sentence-initial purpose and method phrases are frequent:
- "To bridge this gap, we introduce..."
- "By injecting PII into specific model parameters via masked continual pretraining, we obtain a ground-truth for knowledge localization."

---

## SENTENCE-LEVEL PATTERNS

**Correlative pairs for layered reasons:**
> "...not only because the memorized PII itself might be leaked..., but also because of second-order privacy risks..."

**Inline numbered taxonomy inside a sentence:**
> "Existing unlearning approaches for LLMs can be grouped into 1) gradient-based approaches and 2) localize-first, remove-second approaches, which both suffer from weaknesses such as..."

**Hyphenated compound modifiers to name paradigms and levels of analysis.**
This is heavy and characteristic — coin them freely:
*localize-first, unlearn-second*, *output-level*, *parameter-level*,
*gradient-based*, *localization-based*, *post hoc*, *second-order*.

**Concessive openers before a negative result:**
> "...find that, despite strong output-level performance, existing methods are highly imprecise and susceptible to resurfacing attacks."

---

## CLAIM CALIBRATION

- Own empirical results: "we show that", "we find that", "demonstrating that", "our results underscore that"
- Prior work: "several works show that", "a concern reinforced by"
- Speculation, limitations, recommendations: hedge with "may", "could", "it may be preferable to"

Hedging is reserved for limitations and forward-looking recommendations. Do not
hedge established findings.

> "we recognize that knowledge localization may not always be realistic, and that memory storage may not always be very localized in dense models."
> "there is a need for more precise knowledge localization techniques, which could greatly benefit the development of unlearning."

---

## SECTION ENDINGS

**Introductions** close with a summative verdict plus an aspiration for the
artifact — never an abrupt stop:

> "Overall, our results underscore that unlearning has a long way to go in achieving true knowledge erasure. We aspire for Lacuna to serve as a new evaluation testbed for unlearning's localization precision, complementing behavioral evaluations, and to drive further advances in localization-based unlearning methods."

**Conclusions** follow a fixed six-beat arc:
1. Restate the artifact and what it does ("We present X, a ...")
2. State the mechanism that makes it work ("By <gerund>, we obtain ...")
3. State what that enables ("This enables the first quantitative assessment of ...")
4. Findings, including the contrastive baseline ("Our findings underscore that ... In contrast, ...")
5. Future directions ("These findings suggest two important directions for future research. Firstly, ... Secondly, ...")
6. Honest caveat, then a practical recommendation ("At the same time, we recognize that ... Therefore, ...")

Note the community-facing register in closings: "we hope it will encourage the
community to move beyond output-level evaluation."

---

## THINGS TO AVOID

- First person singular ("I")
- Contractions
- Exclamation marks
- Em-dashes for general asides (they are reserved for *e.g.*/*i.e.* glosses)
- Bold for emphasis in body text
- Starting sentences with "And" or "But"
- Casual language or colloquialisms
- Hedging on established results
- Adding docstrings, comments, or "improvements" that were not requested
- Inventing citations — flag when a reference is needed
