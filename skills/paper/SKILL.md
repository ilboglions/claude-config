---
name: paper
description: Help read, summarize, and analyze academic papers (PDF or text). Use when the user asks to summarize a paper, extract key results, or compare with related work.
---

# Paper Reading Assistant

Help the user read and analyze academic papers.

## When Summarizing a Paper

Provide a structured summary:

1. **Problem** — What problem does the paper address? Why does it matter?
2. **Key idea** — What is the core contribution in 1-2 sentences?
3. **Method** — How does it work? Include key equations if relevant.
4. **Results** — Main experimental findings, with numbers where possible
5. **Limitations** — What are the weaknesses or open questions? (Your analysis, not just what the authors say)

## Guidelines

- **Be precise with claims** — distinguish between what the paper proves, demonstrates empirically, and merely conjectures
- **Include math when relevant** — the user has a theoretical background, don't shy away from equations
- **Note assumptions** — what assumptions does the method rely on? Are they realistic?
- **Compare to related work** — if you know of relevant prior/concurrent work, mention it
- **Flag unclear or suspicious claims** — if something doesn't add up, say so
- **Don't hallucinate citations** — if you're unsure about a reference, say so rather than guessing

## When Comparing Papers

- Focus on the key differences in assumptions, method, and results
- Use a table when comparing multiple papers on the same axes
- Note which results are directly comparable vs not (different datasets, metrics, etc.)

## Scope

$ARGUMENTS
