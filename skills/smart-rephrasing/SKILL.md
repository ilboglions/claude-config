---
name: smart-rephrasing
description: Make a passage the user wrote flow better while keeping their own sentences and wording. Reorders sentences, adds connectives and short bridges that state logic the text already implies, and fixes typos and grammar, without adding or removing content. Use when the user asks to rephrase, improve the flow of, smooth out, or better connect their text. Not for free rewrites.
---

# Smart Rephrasing

The user wrote the text, and they decided what it says and which words say it.
Your job is to make the sentences connect, not to rewrite them. The user should
recognize every sentence in the output as their own.

Boundary with `/matteo-writing`: that skill drafts and rewrites academic prose
freely. This one keeps the user's wording and only works on the connections.

## What you may do

1. **Reorder sentences** within a paragraph, e.g. when a sentence relies on a
   definition that comes later, or when two related points are split apart.
   Keep paragraph breaks and paragraph order as they are.
2. **Add or change connectives** between and at the start of sentences.
3. **Merge or split sentences.** Join two sentences with a connective
   ("X. Y." → "X, so Y."), or split one that carries two separate ideas.
4. **Fix references** that are unclear or broken by reordering: a pronoun that
   now comes before its noun, or a "this" with no clear antecedent.
5. **Add a short bridging sentence** when the link between two sentences is
   implied but never stated. It may only say what the text already implies. Use
   these sparingly, rarely more than one per paragraph.
6. **Fix mistakes**: typos, spelling, grammar, agreement, articles,
   prepositions, punctuation, tense consistency.
7. **Use US spelling throughout** ("behavior", "generalize", "modeling",
   "center", "defense"), so the text is consistent even when the input mixes
   US and British forms. Leave proper nouns, quotes, and paper titles as they
   are.

## What you may not do

- Add content: no new claims, facts, examples, numbers, citations, or
  qualifiers.
- Remove content, even when it looks redundant.
- Make claims stronger or weaker ("shows" → "suggests", or adding "clearly").
- Swap the user's words for synonyms or "better" words, or change the register.
  The only exception is a word that is plainly a mistake.
- Touch technical terms, notation, LaTeX commands, math, citations, or
  formatting.
- Apply style rules on your own (e.g. removing contractions). That changes the
  user's wording too.

## Connectives must name the real relation

Every connective you add must state how the two sentences actually relate:
cause ("because", "since"), consequence ("so", "therefore", "as a result"),
contrast ("however", "whereas", "instead"), concession ("although", "even
though"), example ("for example"), specification ("concretely", "in
particular"), condition ("if", "unless"), or sequence ("first", "then").

Avoid "Moreover", "Additionally", "Furthermore", and "Also". They make text
look connected without connecting it. Use one only when a sentence really just
adds a parallel point, and never more than once in a passage. Not every
sentence needs a connective either. Sentences that already follow naturally
stay as they are.

If you cannot tell how two sentences relate, do not guess. The missing link is
probably a missing step in the argument, and supplying it would be adding
content.

## Register

The user says what the text is for (paper, email, review, message). Match that
and the register of the input. For paper prose, the transitions table in
`/matteo-writing` is a good pool of connectives.

## Output

Return only the rephrased text, ready to paste, in the same format as the
input (LaTeX stays LaTeX, Markdown stays Markdown). No preamble, no list of
changes, no marked insertions.

The one exception: if two sentences cannot be connected without adding
content, leave them as they are and add a single line after the text naming the
gap, e.g. *Gap: the link between the threat model and the second experiment is
not stated, so I left it as is.* Write this line only when it applies.

Before returning, compare the output against the original sentence by
sentence. Every piece of content must still be there, nothing new may appear
beyond connectives and bridges, and no claim may have changed in strength.

## Example

Input:
> Our attack outperforms the baseline on all of them. We evaluate on three
> datasets. The baseline use a fixed threshold. We calibrate the threshold on
> held-out data. Membership inference attacks need a threshold.

Output:
> Membership inference attacks need a threshold. The baseline uses a fixed
> threshold, whereas we calibrate it on held-out data. We evaluate on three
> datasets, and our attack outperforms the baseline on all of them.

Here the general statement moves first because the others depend on it. The
two threshold sentences are a contrast, so they are merged with "whereas".
"All of them" now follows the datasets it refers to, and "use" becomes "uses".
No content was added or removed.
