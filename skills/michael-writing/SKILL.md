---
name: michael-writing
description: Apply Michael's academic writing style when drafting or editing text. Use when writing LaTeX prose, paper sections, abstracts, or any academic text for Michael.
---

# Michael Writing Style Guide

Use this guide whenever writing or editing academic text for Michael. Match these patterns exactly. When in doubt, prefer his conventions over generic academic writing defaults.

---

## HARD RULES

### Never use em-dashes
Michael does not natively use em-dashes (---). Do not insert them. Use semicolons, parentheses, commas, or separate sentences instead.

- BAD: "Transformers --- unlike RNNs --- process tokens in parallel."
- GOOD: "Transformers, unlike RNNs, process tokens in parallel."
- GOOD: "Transformers (unlike RNNs) process tokens in parallel."

### Always use "we", never "I"
Even in single-author sections, Michael uses the academic "we" consistently.

### No contractions
Write "do not", "cannot", "it is", etc. Never "don't", "can't", "it's".

### No exclamation marks
Academic tone throughout. No casual interjections.

---

## SENTENCE STRUCTURE

### Topic sentence then elaboration then technical detail
Paragraphs nearly always open with a high-level claim, then narrow to specifics:

> "Transformers are currently the backbone of NLP systems. Modern LLMs and LRMs have at their core an implementation of the Transformer architecture. Being more efficient to train and better at natural language understanding, these models have dominated the application space of NLP since their introduction in 2017."

### Semicolons to join related clauses
Michael heavily uses semicolons to connect two independent but related thoughts rather than splitting them into separate sentences:

> "A large positive eigenvalue indicates a direction of steep curvature (a 'sharp' direction), while a near-zero eigenvalue indicates a flat direction along which the loss barely changes."

> "For a simple task, at small length, there are many heuristic solutions available and thus fewer directions of high curvature along which the loss increases. For a more complex task, even at small length, most eigenvalues are large, meaning that there are few solutions which can minimize the loss successfully."

### Colons to introduce explanations or results
> "This leads to the following question: can transformers simulate the reasoning of more complex finite state machines?"

> "The past works presented here focused on *expressivity*; the future work turns to a complementary and relatively underexplored direction: *learnability*."

### Parenthetical asides (not em-dashes)
He uses actual parentheses heavily for clarifications, examples, and abbreviation introductions:

> "...weighted finite automata (WFAs), a class of models which subsumes DFAs..."
> "...using a more standard transformer implementation, with soft attention and an MLP (multilayer perceptron)..."

---

## TRANSITIONS & CONNECTIVES

### Primary contrast word: "However"
Almost always starts a new sentence. Used very frequently:

> "However, this is not representative of the capacities of transformers."
> "However, little is understood about how they reason and the limits of their computational capabilities."

### Additive: "Moreover", "Furthermore", "In addition"
> "Moreover, this token processing strategy also allows one to parallelize training to a greater degree."
> "Furthermore, seminal work in LLM reasoning showed that..."

### Forward references
- "In what follows, we..."
- "In the following, we..."
- "We now turn our focus to..."
- "We are now ready to state our main results."

### Summative: "Taken together", "Collectively", "In summary"
> "Taken together, these contributions fit into the broader motivation of this PhD thesis."
> "Collectively, our analysis offers principled guidance for designing scalable multi-agent reasoning systems."

### "In order to" (not just "To")
Michael frequently uses "In order to" at the start of sentences, especially when motivating a research direction:

> "In order to understand how transformers implement sequential reasoning..."
> "In order to derive a more fine-grained understanding of this phenomenon..."

---

## KEY PHRASES & IDIOMS

These are phrases Michael uses repeatedly. Incorporate them naturally:

| Pattern | Example |
|---------|---------|
| "In this work, we..." | Opening contribution framing |
| "This leads to the following question:" | Posing research questions explicitly |
| "More precisely, we show that..." | Tightening a claim |
| "We posit that..." | Hedged claims / conjectures |
| "It is worth mentioning that..." | Flagging a notable aside |
| "This naturally leads to..." | Connecting ideas |
| "In light of this," | Drawing consequences |
| "Intuitively," | Before informal explanation |
| "More formally," / "More rigorously," | Before a definition |
| "Note that" / "Note, however, that" | Caveats and remarks |
| "it would be interesting to..." | Future work suggestions |
| "This defies our intuition" | Highlighting a surprising result |
| "This sheds light on..." | Explaining implications |
| "s.t." | Abbreviation for "such that" in math-adjacent prose |
| "i.e." / "e.g." | Italicized, used frequently |

---

## HEDGING & EPISTEMIC MARKERS

Michael hedges claims carefully rather than making flat assertions about uncertain things:

- "We posit that there should exist languages for which these bounds are tight."
- "This may, however, be due to the fact that..."
- "It may be interesting to analyze..."
- "...the results may match more closely the trend predicted by the theory."
- "This is consistent with the intuition that..."

He does NOT hedge when stating proven results or established facts. Hedging is reserved for conjectures, interpretations of experiments, and future directions.

---

## MATHEMATICAL WRITING STYLE

- Gives an intuitive explanation before or after formal definitions: "Intuitively, simulation can be thought of as reproducing the intermediary steps of computation for a given algorithm."
- Uses "s.t." freely in mathematical prose
- Introduces notation blocks systematically: "We denote with... We use bold letters for..."
- Uses "it is easy to see that" and "it follows that" for straightforward consequences
- Labels theorems/propositions and refers back to them by number

---

## EMPHASIS

- Uses `\textit{}` for key technical terms on first substantive use: *expressivity*, *learnability*, *compactly*, *systematic generalization*, *length generalization*
- Uses `\textsc{}` for named tasks/languages: \textsc{Parity}, \textsc{Majority}, \textsc{Sort}
- Does NOT use bold for emphasis in body text (bold is reserved for paragraph headers)

---

## STRUCTURAL PATTERNS

### Research question framing
Michael often builds to an explicit italicized question:

> "This naturally leads to the following question: *can transformers simulate WFAs using a number of layers that is less than linear?*"

### Contribution enumeration
Uses `\begin{itemize}` with concise bullet points for listing contributions, not long prose blocks.

### Section endings
Sections often close with implications or forward pointers, not abrupt stops:

> "We hope that our results may shed some light on the success of transformers for sequential reasoning tasks, and give practical considerations in terms of depth and width of such models for given tasks."

### Future work phrasing
Always framed as open questions or interesting directions, never as definitive plans:

> "It may be interesting to analyze to what extent transformers natively implement the algorithmic reasoning used in our constructions."
> "Empirically or theoretically, it would be interesting to show how the quantity of data, optimization procedure, or various aspects of the target structure can affect the quality of found shortcuts."

---

## THINGS TO AVOID

- Em-dashes (use semicolons, commas, or parentheses)
- First person singular ("I")
- Contractions
- Exclamation marks
- Starting sentences with "And" or "But"
- Casual language or colloquialisms
- Overuse of adverbs (Michael uses them sparingly)
- Excessive hedging on proven results
- Adding docstrings, comments, or "improvements" not requested
- Inventing citations (flag when a reference is needed)
