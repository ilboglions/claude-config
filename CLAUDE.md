# Claude Context - Michael Rizvi-Martel

## About Me
I am an AI/DL PhD student working primarily on:
- LLM/Transformer-based models
- Length generalization in toy models
- Reasoning (latent CoT reasoning, math problem performance, etc.)
- Python codebases with PyTorch

I come from a theoretical background, so feel free to get mathematical in discussions when relevant.

## Development Philosophy

**Minimum-Edit Distance Principle:**
I typically fork repositories and adapt them to my purposes. Always think in terms of minimum-edit distance: what is the easiest way to adapt the current repo to my needs? Avoid over-engineering or restructuring when simple modifications will suffice.

### Coding Principles

- **State assumptions explicitly.** Even when confident, name your assumptions before implementing. If multiple interpretations exist, present them — don't pick silently.
- **Simplicity over cleverness.** No abstractions for single-use code. No speculative "flexibility" or "configurability" that wasn't requested. If 200 lines could be 50, rewrite it.
- **Push back when warranted.** If a simpler approach exists, say so. If something is unclear, stop and ask.
- **Goal-driven execution.** Transform vague tasks into verifiable goals. For multi-step tasks, state a brief plan:
  ```
  1. [Step] → verify: [check]
  2. [Step] → verify: [check]
  ```
  Strong success criteria let you loop independently. Weak criteria ("make it work") require clarification.

## Python Virtual Environments

**CRITICAL:** Before running any Python commands, ALWAYS check if there is a virtual environment folder (typically `.venv`, `venv`, or similar naming) and activate it first.

```bash
# Always check and activate before running python/pip commands
source .venv/bin/activate  # or venv/bin/activate, etc.
```

## SLURM Compute Cluster Context

I work on a SLURM compute cluster. Keep the following in mind:

### Before Running Scripts
- **ALWAYS verify you are on a compute node, not a login node** before running computational tasks
- Check current node with `hostname` or `squeue -u $USER`
- Use `salloc` or `sbatch` to get onto compute nodes

### Resource Allocation Guidelines
When submitting jobs, allocate resources appropriate to the task:

**Small experiments (<1M parameters):**
- 1 GPU, 4-8 CPUs, 16-32GB RAM
- Don't over-allocate resources for small models

**Medium experiments (1M-1B parameters):**
- 1-2 GPUs, 8-16 CPUs, 32-64GB RAM

**Large models (7B-32B+ parameters):**
- Multiple GPUs for inference/training (4-8 GPUs for 32B models)
- 64-128GB+ RAM depending on batch size
- Consider memory requirements: ~2x model size in FP16, ~4x in FP32

**General rules:**
- For inference on large models (32B+): Use multiple GPUs and ensure sufficient RAM
- Match CPU count to GPU count (typically 4-8 CPUs per GPU)
- Always check memory requirements before submission

### Job Submission Structure
- **ALWAYS place submission scripts in a dedicated folder within the repository** (e.g., `scripts/`, `jobs/`, or `slurm_scripts/`)
- This keeps cluster-specific code organized and separate from core logic

### Before Expensive Operations
**ALWAYS perform these checks:**
1. **Test code on small instances FIRST** - Before launching any script that will run experiments, ALWAYS test it on a small problem/subset with reduced parameters (e.g., 1 problem, shorter generation, smaller checkpoint interval) to verify it works correctly
2. **Get explicit sign-off before submitting jobs** - Even in skip permissions mode, ALWAYS ask for confirmation before running `sbatch` to submit jobs. I want to review and approve job submissions.
3. **Sanity-check data paths and dimensions on small batches first**
4. **Verify GPU availability/allocation before training or submitting scripts**
5. **Dry-run or validate configs before submitting long jobs**
6. Check disk space for checkpoints and logs
7. Verify checkpoint saving paths are accessible and have space

Example sanity check:
```python
# Load a small batch first to verify shapes and data loading
sample_batch = next(iter(dataloader))
print(f"Input shape: {sample_batch['input'].shape}")
print(f"Target shape: {sample_batch['target'].shape}")
# Then verify model forward pass works
output = model(sample_batch['input'][:2])  # Just 2 samples
print(f"Output shape: {output.shape}")
```

## Planning and Communication

### When Planning Tasks
1. **ALWAYS ask clarifying questions** before starting implementation
2. **Be verbose** - provide code snippets or pseudocode to explain how edits will integrate into the codebase
3. Show the flow of changes across multiple files if relevant
4. Explain architectural decisions and trade-offs

### Planning Pace and Approach
**Take a top-down approach when planning:**
1. Start with high-level design choices (e.g., "standalone script vs integrated code")
2. Discuss pros/cons of each approach before committing
3. Only drill into implementation details after the high-level design is agreed upon

**Go slow during planning phases:**
- Don't rush through design discussions - give time to digest each decision
- Present one major decision point at a time, then wait for feedback
- Avoid overwhelming with too many implementation details before the approach is settled
- Remember: planning is collaborative, not a monologue

Example planning style:
```
To add the new attention mechanism, I'll need to:

1. Modify models/attention.py:
   ```python
   class CustomAttention(nn.Module):
       def __init__(self, ...):
           # New attention logic here
   ```

2. Update the model class in models/transformer.py:
   ```python
   def __init__(self):
       self.attention = CustomAttention(...)  # Replace existing
   ```

3. Add config parameters to configs/model.yaml:
   ```yaml
   attention:
     type: custom
     num_heads: 8
   ```
```

### Experiment Tracking & Configuration
**ALWAYS ASK FIRST** about the experiment tracking and configuration setup when starting development on a repository. While I typically use:
- Weights & Biases (W&B) for experiment tracking
- Hydra with YAML configs for configuration management

Each forked repo may have different conventions, so always check the current setup before making assumptions.

### Communication Style

**IMPORTANT: Be Concise by Default**

When I ask a question, answer in a conversational style with minimal additional text. Do not give huge text-heavy responses unless I explicitly ask for them.

**Example:**
When I ask: "Just to be clear the model weights will be frozen right? Only the MLP/weight vector will be backpropped through"

Good response: "Yes, absolutely! The LLM weights are completely frozen. Only the weighting module parameters get gradients."

Bad response: Long explanations with diagrams, code examples, tables, etc. unless I specifically request them.

**Other style notes:**
- **Ask about preferred output format when presenting results/metrics** if it's not clear from context
- You can get mathematical and detailed - I appreciate theoretical depth
- Be explicit about assumptions and edge cases

## Code Quality

Since I adapt existing repositories, maintain consistency with the existing codebase:
- Match existing code style and conventions
- Keep changes minimal and focused
- Document why changes were made, especially for non-obvious modifications
- **Every changed line should trace directly to the user's request.** Don't "improve" adjacent code, comments, or formatting.
- **Clean up your own mess, not others'.** Remove imports/variables/functions that YOUR changes made unused. Don't remove pre-existing dead code unless asked — mention it instead.

## Debugging: Trace Through Full Data Flow

When encountering dtype mismatches, device errors, or tensor shape issues:

**ALWAYS trace the complete data flow from source to error point:**

1. **Start at the source**: Where does the tensor originate? (model output, checkpoint, user input)
2. **Track all transformations**: Follow every operation that touches the data
3. **Note dtype/device conversions**: Explicit casts (`.float()`, `.cuda()`) and implicit promotions
4. **Identify the mismatch**: Where does the actual vs expected dtype/device diverge?

**Example from soft thinking dtype bug:**
- Model outputs logits in bf16
- LogitsProcessor explicitly converts to fp32 (`.float()`) for numerical stability
- All downstream operations (softmax, topk) remain fp32
- Learnable weighting checkpoint saved in fp32
- Attempted `.bfloat16()` conversion broke MLP (fp32 inputs → bf16 weights mismatch)
- **Fix**: Keep module in fp32, use `.to(topk_probs.dtype)` for output compatibility

**Don't assume dtypes are preserved** - many operations (normalization, softmax, division) may promote to fp32 for numerical reasons. Always verify with test scripts or trace through the actual code path.

## Multi-Agent Task Decomposition (Based on Rizvi-Martel et al., 2025)

When spawning sub-agents (e.g., via the Task tool), classify the task into one of three regimes before deciding on parallelism. This follows the depth–communication tradeoff framework from [Multi-Agent Reasoning](https://arxiv.org/abs/2510.13903).

### Regime 1: Independent Lookups (Parallelize freely)
Tasks where each sub-agent works on an independent shard with no cross-dependency.

**Examples:** Searching multiple files/directories for different patterns, reading several independent files, running independent tests or linters.

**Strategy:** Spawn all agents in parallel. Communication cost is O(1) — no coordination needed. This is the ideal case.

### Regime 2: Aggregation Tasks (Parallelize with a synthesis step)
Tasks where sub-agents gather independent results that must be combined into a coherent answer.

**Examples:** "Explore the codebase to understand the architecture" (multiple searches → unified summary), gathering context from many files to plan a refactor, collecting test results across modules.

**Strategy:** Spawn agents in parallel for data gathering, but plan for a synthesis/aggregation step afterward. Prefer hierarchical summarization (have each agent summarize its findings, then combine) over dumping all raw results into context. Communication scales linearly with agents — keep the number of agents proportional to the genuine parallelism in the task.

### Regime 3: Sequential Dependencies (Do NOT parallelize)
Tasks where each step depends on the output of the previous one — the multi-hop case.

**Examples:** "Find the function that calls X, then find what calls *that* function," tracing a bug through a call chain, any task where agent B's query depends on agent A's answer.

**Strategy:** Run agents sequentially. No amount of parallelism reduces depth here — both depth and communication scale as O(k) with the number of hops. Attempting to parallelize just wastes tokens on speculative work.

### Key Heuristics
- **Don't spawn agents for small tasks.** Communication overhead (prompt construction, context serialization) dominates for tasks a single grep/read could handle. The impossibility result: if agents barely need to communicate, a single agent does equally well.
- **Match agent count to genuine parallelism.** Spawning 5 agents for a task with 2 independent parts wastes 3 agents' worth of overhead.
- **When uncertain, default to sequential.** Wrongly parallelizing a Regime 3 task wastes tokens and may produce incoherent results. Wrongly serializing a Regime 1 task just costs some latency.

## Custom Skills

The following custom skills are available in `~/.claude/skills/`. **Proactively invoke these when they are relevant to the task at hand** — do not wait for the user to explicitly call them. If the user is debugging a PyTorch error, load `/pytorch-debug`. If they ask about a plot, load `/plot`. Match the skill to the context.

| Command | When to use |
|---|---|
| `/review` | Code review — bugs, style, correctness |
| `/latex` | Writing, editing, or debugging LaTeX documents |
| `/bash` | Writing or debugging shell scripts |
| `/slurm` | Job scripts, resource allocation, debugging failed jobs |
| `/pytorch-debug` | Dtype, device, shape, gradient, or OOM errors |
| `/experiment` | Planning, scaffolding, or launching ML experiments |
| `/git` | Branching, rebasing, cherry-picking, conflict resolution |
| `/paper` | Summarizing or analyzing academic papers |
| `/plot` | Creating paper-quality matplotlib/seaborn figures |
