---
name: plot
description: Help create paper-quality plots and figures with matplotlib or seaborn. Use when the user asks for plots, figures, or visualizations.
---

# Plotting Assistant

Help the user create publication-quality figures.

## Defaults

- Use **matplotlib** + **seaborn** unless the user requests something else
- Default to PDF/SVG export for papers (vector formats)
- Use `plt.tight_layout()` or `constrained_layout=True` to avoid clipping

## Paper-Quality Checklist

- **Readable font sizes** — axis labels ~12pt, tick labels ~10pt, legend ~10pt. Scale up for posters/slides.
- **Colorblind-safe palettes** — prefer seaborn's `colorblind`, `deep`, or manually chosen distinct colors. Avoid red/green as sole differentiator.
- **Consistent styling** — if multiple figures go in the same paper, use the same colors, fonts, and line styles across all of them
- **Meaningful labels** — no `label_1`, no default axis names. Every axis labeled with units where applicable.
- **Legends that help** — place legends where they don't occlude data. Use labels that match the paper's terminology.
- **Error bars / confidence intervals** — always include when showing aggregated results. State what they represent (std, SEM, 95% CI).
- **No chartjunk** — remove unnecessary gridlines, borders, and decoration. Less is more.

## Common Plot Types

- **Training curves**: loss/accuracy vs step/epoch, with smoothing if noisy
- **Bar charts**: comparing methods/baselines, with error bars
- **Scatter plots**: correlation between metrics
- **Heatmaps**: confusion matrices, attention maps, hyperparameter sweeps
- **Multi-panel figures**: use `plt.subplots()` with shared axes where appropriate

## Guidelines

- **Read existing plotting code first** — match the style if figures already exist in the project
- **Save figures to a sensible path** — e.g. `figures/` or `plots/`
- **Use `fig, ax` API** — not `plt.plot()` directly. This makes multi-panel and customization easier.

## Scope

$ARGUMENTS
