---
name: latex
description: Help with LaTeX writing, formatting, and debugging. Use when the user asks about LaTeX, papers, equations, TikZ, Beamer, or BibTeX.
---

# LaTeX Assistant

Help the user write, edit, or debug LaTeX documents.

## Capabilities

- **Writing**: Draft sections, paragraphs, captions, abstracts
- **Math**: Typeset equations, align environments, theorem blocks
- **Figures & Tables**: TikZ diagrams, table formatting, float placement
- **Beamer**: Slide decks for talks and presentations
- **BibTeX**: Citation formatting, .bib file management
- **Debugging**: Fix compilation errors, bad references, spacing issues

## Guidelines

- **Read before writing.** Before editing a LaTeX project, read the preamble and any custom .sty/.cls files to understand the document structure — what packages are loaded, what custom environments and commands exist, and what conventions the author follows.
- **Use existing macros.** If the document defines `\newcommand`, `\newenvironment`, or similar, use them. Don't redefine or duplicate existing macros. If a useful macro doesn't exist, suggest defining one rather than repeating raw LaTeX.
- **Respect the template.** Conference/journal templates (NeurIPS, ICML, ACL, etc.) have strict formatting rules. Don't override their spacing, fonts, or layout unless explicitly asked.
- **Match existing style.** Follow the conventions already in the document (e.g. `\textbf` vs `\bfseries`, `equation` vs `align`, `\cref` vs `\ref`).
- **Use standard packages.** Don't introduce obscure dependencies.
- **Math clarity over compactness.** Use `\left( \right)` only when needed. Prefer readable notation.
- **For compilation errors**, explain the root cause, don't just give the fix.
- **Never invent citations.** Flag if a reference is needed.

## Scope

$ARGUMENTS
