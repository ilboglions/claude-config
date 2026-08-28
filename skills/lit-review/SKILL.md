---
name: lit-review
description: Help search, triage, and synthesize a body of literature into related-work framing. Use when the user asks to find related work, survey a topic, position a paper against prior work, or figure out what has already been done.
---

# Literature Review Assistant

Help the user find, triage, and synthesize literature. This is about surveying a
*body* of work; use `/paper` instead to analyze a single paper in depth.

## Search Strategy

Start from anchors, not from keywords:

1. **Pick 2-3 anchor papers** the user already trusts. Ask for them if not given.
2. **Search backward** — what do the anchors cite for this specific claim?
3. **Search forward** — who cites the anchors? Semantic Scholar and Google Scholar
   "cited by" surface the recent work that keyword search misses.
4. **Then keyword search**, using the terminology the anchors actually use. Field
   vocabulary drifts; "machine unlearning" and "knowledge editing" and "concept
   erasure" overlap heavily but cite each other inconsistently.
5. **Check the venues directly** for the last 2-3 cycles — NeurIPS, ICML, ICLR,
   COLM, ACL/EMNLP/NAACL for ML; IEEE S&P, USENIX Security, CCS for privacy and
   security work. Cross-community work is the easiest to miss.

Flag when a search is likely incomplete rather than presenting it as exhaustive.

## Triage

For each candidate, extract only what decides inclusion:

- **Claim** — what does it actually establish, in one sentence?
- **Evidence type** — proof, empirical result, or conjecture?
- **Relation to the user's work** — baseline, contrasting method, orthogonal, or
  a direct scoop?

Sort into: *must cite and engage*, *cite in passing*, *not relevant*. Say which
bucket and why. Do not summarize papers the user will not use.

## Synthesis

**Organize by axis, never by paper.** A related-work section that walks through
one paper per paragraph is a bibliography, not an argument. Group by the
dimension that matters — threat model, level of analysis, what is assumed known,
what is being measured — and place multiple papers within each.

- Name the axis explicitly before listing work along it
- State where the user's contribution sits on each axis
- Identify the gap as something the axes make visible, not as an assertion
- Note genuine disagreements in the literature; do not flatten them into consensus

## Guidelines

- **Never invent citations.** If a paper is half-remembered, say so and search
  for it. A plausible-looking fabricated reference is the worst failure mode here.
- **Verify every citation resolves** to a real paper with the claimed authors,
  venue, and year before it goes into a draft.
- **Distinguish what a paper proves from what it claims** — the abstract usually
  overstates the theorem.
- **Prefer the peer-reviewed version** over the arXiv preprint when both exist;
  results and claims often changed between them.
- **Watch for concurrent work.** Anything within ~6 months is concurrent, not
  prior; frame it as such rather than as something the user failed to build on.
- **Note retracted, superseded, or failed-to-replicate work** rather than citing
  it neutrally.
- **Be honest about scooping.** If prior work already does what the user
  proposes, say so plainly and early.
