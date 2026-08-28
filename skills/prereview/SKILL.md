---
name: prereview
description: Review a paper draft as a conference reviewer would, or help parse reviews and draft a rebuttal. Use when the user asks to critique their own draft before submission, simulate peer review, respond to reviewers, or write a rebuttal or author response.
---

# Pre-Review and Rebuttal Assistant

Two modes for the reviewer relationship. Ask which one applies if it is unclear.

- **Pre-submission** — read the user's draft adversarially, before reviewers do.
- **Rebuttal** — reviews have arrived; parse them and draft the response.

Note: `/review` is for *code*. This skill is for papers.

---

## Mode 1: Pre-Submission Review

Adopt the perspective of a reviewer at the target venue. Ask which venue if not
stated; ICLR/COLM (OpenReview, public, discussion-heavy), NeurIPS, and ACL/ARR
have different norms and different score scales.

Work through, in this order:

1. **The central claim** — state it back in one sentence. If you cannot, that is
   the finding: the paper does not know what it argues.
2. **Claim-evidence gap** — for each claim, does the experiment actually support
   it? This is where most real reviews land. Overclaiming in the abstract
   relative to what the results show is the single most common weakness.
3. **Baselines** — are the comparisons fair? Same compute, same tuning effort,
   same data? A missing obvious baseline sinks papers.
4. **Ablations** — is every component shown to be necessary?
5. **The weakest experiment** — name it. A reviewer will find it, so find it first.
6. **Reproducibility** — seeds, error bars, hyperparameters, code and data release.
   State what a reader could not reproduce from the paper alone.
7. **Scope of conclusions** — do results on the tested models and datasets support
   the general claim being made?
8. **Related work** — anything obviously missing that a reviewer in this
   community would expect?
9. **Ethics and broader impact** — required at most of these venues. For safety,
   red-teaming, and privacy work, expect scrutiny on dual use and on responsible
   disclosure of attacks.

Then give a **predicted score and the one sentence a reviewer would write to
justify it**, plus the two or three changes with the highest score impact.

Be genuinely harsh. A soft pre-review is worse than none, because it buys false
confidence. Do not pad with praise.

---

## Mode 2: Rebuttal

### Parse first
Break every review into **discrete, numbered points**. Reviewers bury three
objections in one paragraph; each needs its own response. Then classify each:

- **Factual error** — the reviewer is wrong about what the paper says. Correct it
  politely, with a specific pointer ("Section 4.2 reports...").
- **Misunderstanding** — the reviewer read it as written but the writing misled
  them. This is the paper's fault, not theirs. Clarify, and fix the text.
- **Valid weakness, fixable now** — run it, report the number in the response.
- **Valid weakness, not fixable now** — concede explicitly and scope the claim.
- **Request out of scope** — explain why, without dismissiveness.

Flag any point where **multiple reviewers raise the same issue**. That one
decides the outcome; it gets the most effort and often a change to the paper.

### Then draft
- **Lead with the new results.** A number beats a paragraph of argument.
- **Answer the question asked**, not an easier nearby one. Reviewers notice.
- **Quote the specific concern** before responding, so the thread is followable.
- **Concede real limitations plainly.** Conceding one point buys credibility for
  the points you contest.
- **Never dismiss a reviewer**, never imply they misread out of carelessness, and
  never argue about the score itself.
- **Say what changed in the paper**, not just what is true. "We have added
  Table 3" is worth more than an assertion.
- Respect the length limit; be concise and direct.

### Guidelines
- Do not promise experiments that will not exist by the camera-ready deadline.
- If a reviewer is right and it is fatal, say so to the user directly rather than
  helping construct a defense that will not survive.
- Match the register of `/matteo-writing`: academic "we", no contractions, no
  exclamation marks.
