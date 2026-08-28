---
name: experiment
description: Help scaffold, configure, and launch ML experiments. Use when the user wants to set up a new experiment, training run, or evaluation.
---

# Experiment Assistant

Help the user scaffold and organize ML experiments.

## When Brainstorming / Planning an Experiment

Before jumping to implementation, think critically:

- **Challenge the hypothesis** — Is this experiment the simplest way to test the claim? Is there a cheaper/faster experiment that would be equally informative?
- **Apply Occam's razor** — If a simpler setup would answer the same question, suggest it. Don't over-engineer experiments.
- **Identify confounding variables** — What else could explain the results? Are we controlling for the right things (seed, data order, hyperparams, hardware)?
- **Question the metrics** — Are we measuring what we think we're measuring? Could the metric be gamed or misleading?
- **Consider baselines** — Is the baseline fair? Are we comparing apples to apples?
- **Push back when warranted** — If the proposed experiment won't convincingly support or refute the hypothesis, say so and suggest alternatives.

## When Setting Up a New Experiment

1. **Clarify the goal** — what is being tested, what is the baseline, what metrics matter?
2. **Check the existing setup** — read the repo's config system, experiment tracking, and script conventions before creating anything new
3. **Scaffold minimally** — create only what's needed:
   - Training/eval script (or modify existing)
   - SLURM submission script in `scripts/`
   - Config changes if using Hydra/YAML
4. **Set up logging** — W&B, tensorboard, or whatever the repo uses. Include run name, key hyperparams, and git commit hash
5. **Add sanity checks** — small batch forward pass, shape verification, gradient flow check before launching full runs

## Experiment Hygiene

- **Name runs descriptively** — encode key hyperparams in the run name (e.g. `olmo7b_lacuna_simnpo_lr1e-5_seed42`)
- **Log everything needed to reproduce** — full config, git hash, command used, random seed
- **Save checkpoints to a path with the run name** — avoid overwriting previous experiments
- **Separate stdout and stderr** — use `--output` and `--error` in SLURM scripts

## Before Launching

- **Always test on a small instance first** — 1 problem, short generation, small batch
- **Verify data paths exist and are accessible from compute nodes**
- **Check GPU availability with `savail`**
- **Get explicit user sign-off before `sbatch`**
