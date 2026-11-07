#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Stage 1 evaluation glue: runs harness.evaluate_item with an MLX model.

Run with the Stage 1 virtual environment's Python (mlx-lm installed there), through the
shared heavy-build gate, in bounded chunks (--start / --limit):

  zsh .../mini-heavy-gate.sh model "$VENV/bin/python" stage1/run_eval.py \\
      --model MODEL_DIR [--adapter ADAPTER_DIR] --data DATA_DIR --split dev \\
      --engine PATH/marty-solid --engine-commit 76104dea --out RESULTS.jsonl --start 0 --limit 25

Greedy decoding (temperature 0), at most --max-tokens per answer, at most 3 repairs.
Each result line records the model, adapter, versions and the measured time, tokens and
peak memory per attempt. Results are appended to a new file per chunk (never
overwritten).
"""

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
import generate_components as gc  # noqa: E402
import harness  # noqa: E402


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter")
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--engine", required=True)
    ap.add_argument("--engine-commit", required=True)
    ap.add_argument("--out", required=True, help="new JSON Lines file for this chunk")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--max-repairs", type=int, default=3)
    a = ap.parse_args(argv)
    if os.path.exists(a.out):
        ap.error(f"{a.out} exists; refusing to overwrite")

    import mlx.core as mx  # noqa: E402  (only in the Stage 1 virtual environment)
    import mlx_lm  # noqa: E402
    from mlx_lm.sample_utils import make_sampler  # noqa: E402

    with open(os.path.join(a.data, a.split + ".jsonl"), encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    with open(os.path.join(a.data, a.split + ".meta.jsonl"), encoding="utf-8") as f:
        metas = [json.loads(line) for line in f]
    items = list(zip(rows, metas))[a.start:a.start + a.limit]

    t0 = time.perf_counter()
    model, tokenizer = mlx_lm.load(a.model, adapter_path=a.adapter)
    load_seconds = time.perf_counter() - t0
    sampler = make_sampler(temp=0.0)

    # Choose the prompt form that is an exact prefix of mlx-lm's training render (the
    # tokenizer here is mlx-lm's wrapper, as in training); check_template.py proves the
    # same mode for every training row. Refuse to evaluate otherwise.
    mode, mode_kwargs, _, _ = harness.prompt_mode(tokenizer, rows[0]["messages"])
    if mode is None:
        raise SystemExit("no evaluation prompt is a prefix of the training render; refusing to evaluate")

    def prompt_ids(messages):
        return list(tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_dict=False,
                                                  **mode_kwargs))

    def generate(user):
        ids = prompt_ids([{"role": "user", "content": user}])
        mx.reset_peak_memory()
        start = time.perf_counter()
        text, last = "", None
        for response in mlx_lm.stream_generate(model, tokenizer, prompt=ids, max_tokens=a.max_tokens,
                                               sampler=sampler):
            text += response.text
            last = response
        seconds = time.perf_counter() - start
        return text, {"seconds": round(seconds, 3), "promptTokens": last.prompt_tokens if last else len(ids),
                      "outputTokens": last.generation_tokens if last else 0,
                      "promptTps": round(last.prompt_tps, 1) if last else None,
                      "generationTps": round(last.generation_tps, 1) if last else None,
                      "finish": last.finish_reason if last else None,
                      "peakMemoryGB": round(mx.get_peak_memory() / 1e9, 3)}

    engine = gc.Engine([a.engine], a.engine)
    run = {"model": os.path.abspath(a.model), "adapter": os.path.abspath(a.adapter) if a.adapter else None,
           "adapterSha256": file_sha(os.path.join(a.adapter, "adapters.safetensors")) if a.adapter else None,
           "mlx": mx.__version__, "mlxLm": mlx_lm.__version__, "engineCommit": a.engine_commit,
           "checkerSha256": engine.sha256, "loadSeconds": round(load_seconds, 2), "maxTokens": a.max_tokens,
           "promptMode": mode, "hasThinking": bool(getattr(tokenizer, "has_thinking", False))}
    try:
        with open(a.out, "x", encoding="utf-8") as out:
            for row, meta in items:
                user = row["messages"][0]["content"]
                result = harness.evaluate_item(meta, user, generate, engine.check, a.max_repairs)
                out.write(json.dumps({**result, "run": run}, sort_keys=True) + "\n")
                out.flush()
    finally:
        engine.close()
    print(json.dumps({"items": len(items), "out": a.out, **run}, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
