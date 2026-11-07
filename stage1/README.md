# Stage 1: first small local QLoRA comparison

Approved by the owner on 2026-11-07 ([DATA.md](../DATA.md) §0). Two 4-bit open bases,
the same prose-free engine-generated data, the same small QLoRA settings, the same
evaluation. Everything large (virtual environment, model files, adapters, data, results)
lives in a folder **outside the repository**, called `$STAGE` below. Nothing from
`$STAGE` is committed except small receipts and the results summary.

## What it measures, and what it does not

Measured, per model, on a development split made by the same generator with other
seeds (not the sealed sets):

* engine acceptance on the first try and within 3 repairs (`marty-solid check` at
  MartyGraphics 76104dea; `--strict` does not exist at that commit yet);
* correctness: for `author.ratio`, the engine's solved ratio equals the asked ratio and
  the fixed values are kept; for `author.params` and `repair`, the accepted scene keeps
  exactly the intended values;
* repairs used, seconds per answer, output tokens per second and peak memory, on the
  M1 mini (8 GB), as measured by MLX and `/usr/bin/time -l`.

Not measured: explanation text (no prose in Stage 1 data, by the owner's rule), the
sealed evaluation sets, iPad speed, and anything about strength or real-world physics.

## Data (`make_data.py`)

The user turn is a few `key: value` lines; the answer is scene JSON. No system prompt,
no sentences, no teaching steps; the scene title is the component id.

| Task | Asks for | Correct when |
| --- | --- | --- |
| `author.ratio` (spurPair, planetaryStage) | a target ratio for one part, with some values fixed | engine accepts and its solved ratio equals the target; fixed values kept (many answers can be right) |
| `author.params` (sliderCrank, propeller) | explicit parameter values | engine accepts; values kept exactly |
| `repair` | a refused scene and the engine's reason (one known mutation) | engine accepts; the original values are restored |

Default sizes: train 1,300, valid 100 (for the training loss), dev 100 (for evaluation),
mix about 3 : 3 : 1 : 1 : 4 (spur ratio, planetary ratio, crank, propeller, repair).
Splits never share a target scene.

## Procedure

Run every heavy step through the shared heavy-build gate (`mini-heavy-gate.sh model …`),
in short chunks, so the gate is never held for long. While the disk has less than 10 GB
free, keep only **one** base model on disk at a time and keep at least 4 GB free.

```sh
# 1. Isolated environment (no global installs), pinned versions
python3 -m venv "$STAGE/venv"
"$STAGE/venv/bin/pip" install --no-cache-dir mlx==0.32.4 mlx-lm==0.32.2
"$STAGE/venv/bin/pip" freeze > "$STAGE/receipts/pip-freeze.txt"
export HF_HOME="$STAGE/hf"   # keep the Hub cache inside $STAGE

# 2. One base model (pinned revision, disk check, sha256 check, receipt)
"$STAGE/venv/bin/python" stage1/download.py --repo ibm-granite/granite-4.2-3b-q4-mlx \
  --revision 0c6f39b1827afd5eb2c1c3b13751929857434953 --dest "$STAGE/models/granite" \
  --receipt "$STAGE/receipts/download-granite.json"

# 3. Data (engine calls; through the gate)
gate python3 stage1/make_data.py --engine "$ENGINE" --engine-commit 76104dea --out-dir "$STAGE/data/v1" --seed 1

# 4. Untrained reference (small), then training chunks, then evaluation chunks
gate "$STAGE/venv/bin/python" stage1/run_eval.py --model "$STAGE/models/granite" --data "$STAGE/data/v1" \
  --engine "$ENGINE" --engine-commit 76104dea --out "$STAGE/runs/granite-base-0.jsonl" --start 0 --limit 20
gate "$STAGE/venv/bin/python" stage1/train_chunk.py --model "$STAGE/models/granite" --data "$STAGE/data/v1" \
  --config stage1/lora.yaml --chunk 1 --iters 100 --adapters "$STAGE/adapters/granite"
#    ... chunk 2, 3, ... (each resumes from the previous chunk's adapter)
gate "$STAGE/venv/bin/python" stage1/run_eval.py --model "$STAGE/models/granite" \
  --adapter "$STAGE/adapters/granite/chunk-N" --data "$STAGE/data/v1" --engine "$ENGINE" \
  --engine-commit 76104dea --out "$STAGE/runs/granite-lora-0.jsonl" --start 0 --limit 25
#    ... --start 25, 50, 75
python3 stage1/summarize.py "$STAGE"/runs/granite-lora-*.jsonl

# 5. Delete our own Granite files if the disk is short, then repeat 2-4 for Qwen3.5-4B
#    (mlx-community/Qwen3.5-4B-MLX-4bit at 32f3e8ecf65426fc3306969496342d504bfa13f3)
```

## Bases

| Base | Repository and revision | Size | Licence (model card, checked 2026-11-07) | Notes |
| --- | --- | --- | --- | --- |
| IBM Granite 4.2 3B | `ibm-granite/granite-4.2-3b-q4-mlx` @ `0c6f39b1…` (IBM's own 4-bit MLX build of `ibm-granite/granite-4.2-3b`) | 2.07 GB | Apache-2.0 | `granite` architecture, 40 layers, hidden 2560 |
| Qwen3.5-4B | `mlx-community/Qwen3.5-4B-MLX-4bit` @ `32f3e8ec…` (community 4-bit MLX conversion of `Qwen/Qwen3.5-4B`, whose repo has the Apache-2.0 `LICENSE` file) | 3.06 GB | Apache-2.0 | `qwen3_5`, vision-language checkpoint with hybrid linear/full attention; mlx-lm 0.32.2 has `qwen3_5.py`; text-only loading is checked at the first run |

Apache-2.0 allows fine-tuning and redistribution of derivatives (with the licence text,
notices and a statement of changes). Nothing is redistributed in Stage 1.

## Settings (`lora.yaml`)

QLoRA (LoRA on the 4-bit base): rank 8, scale 20, 16 layers, batch 1, learning rate
1e-4 (constant), sequence length 1,024, gradient checkpointing, loss on the answer only.
Smaller than [PLAN.md](../PLAN.md) §5 (rank 16) because the mini has 8 GB and is shared.
Each chunk is at most 400 iterations; chunk *k* uses data-order seed *k*.

## Receipts

`download.py`, `train_chunk.py` and `run_eval.py` each write a receipt (versions,
revision, file sizes and SHA-256, seconds, peak memory, losses, adapter SHA-256). The
results page for Stage 1 quotes these receipts; anything not measured is marked so.
