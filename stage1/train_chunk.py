#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run ONE bounded QLoRA training chunk with mlx-lm and write a receipt.

Each chunk is a separate heavy-gate job (the gate is shared; do not hold it for hours):

  zsh .../mini-heavy-gate.sh model "$VENV/bin/python" stage1/train_chunk.py \\
      --model "$STAGE/models/granite-4.2-3b-q4" --data "$STAGE/data/v1" \\
      --config stage1/lora.yaml --chunk 1 --iters 100 \\
      --adapters "$STAGE/adapters/granite" [--keep-free-gb 3] [--timeout-minutes 40]

Data order: one fixed shuffle of train.jsonl (seed "stage1-order"); chunk k trains on
the next `iters` rows of that order (wrapping to a new pass at the end), written to
ADAPTERS/chunk-k/data/. So no row repeats until every row was seen once. With batch
size 1 each row is used once per chunk. The optimizer state (Adam) starts fresh in each
chunk; the learning rate is constant. Chunk k resumes from chunk k-1's adapter.

The receipt (ADAPTERS/chunk-k/receipt.json) records the command, versions, seconds,
max RSS, the last train/validation loss, tokens/s and peak memory (from the metrics
callback in lora_runner.py), the rows used, and the adapter SHA-256.
"""

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def chunk_rows(lines, chunk, iters):
    """Rows for chunk k (1-based): consecutive slice of a fixed shuffle, wrapping around."""
    order = list(range(len(lines)))
    random.Random("stage1-order").shuffle(order)
    start = (chunk - 1) * iters
    return [lines[order[(start + i) % len(order)]] for i in range(iters)], start


def summarize_metrics(path):
    train, val = [], []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                (train if row["kind"] == "train" else val).append(row)
    last_t = train[-1] if train else {}
    return {"trainLoss": last_t.get("train_loss"), "valLoss": val[-1].get("val_loss") if val else None,
            "tokensPerSecond": last_t.get("tokens_per_second"),
            "peakMemoryGB": max((r.get("peak_memory") or 0 for r in train), default=None),
            "trainedTokens": last_t.get("trained_tokens"), "reports": len(train) + len(val)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--chunk", type=int, required=True)
    ap.add_argument("--iters", type=int, required=True)
    ap.add_argument("--adapters", required=True)
    ap.add_argument("--keep-free-gb", type=float, default=3.0)
    ap.add_argument("--timeout-minutes", type=float, default=40.0)
    a = ap.parse_args(argv)
    if a.chunk < 1 or not 1 <= a.iters <= 400:
        ap.error("--chunk must be >= 1 and --iters 1..400 (keep each gate job short)")
    if not 1 <= a.timeout_minutes <= 60:
        ap.error("--timeout-minutes must be 1..60")
    out = os.path.join(a.adapters, f"chunk-{a.chunk}")
    prev = os.path.join(a.adapters, f"chunk-{a.chunk - 1}", "adapters.safetensors")
    if os.path.exists(out):
        ap.error(f"{out} exists; refusing to overwrite")
    if a.chunk > 1 and not os.path.exists(prev):
        ap.error(f"missing previous chunk {prev}")
    os.makedirs(a.adapters, exist_ok=True)
    if shutil.disk_usage(a.adapters).free < a.keep_free_gb * 1e9:
        raise SystemExit(f"less than {a.keep_free_gb} GB free; not starting")

    # This chunk's data: its slice of the fixed order, plus the full validation file.
    with open(os.path.join(a.data, "train.jsonl"), encoding="utf-8") as f:
        lines = f.read().splitlines()
    rows, start = chunk_rows(lines, a.chunk, a.iters)
    data_dir = os.path.join(out, "data")
    os.makedirs(data_dir)
    with open(os.path.join(data_dir, "train.jsonl"), "x", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    shutil.copyfile(os.path.join(a.data, "valid.jsonl"), os.path.join(data_dir, "valid.jsonl"))

    metrics = os.path.join(out, "metrics.jsonl")
    cmd = [sys.executable, os.path.join(HERE, "lora_runner.py"), "--metrics", metrics,
           "--model", a.model, "--train", "--data", data_dir, "-c", a.config, "--iters", str(a.iters),
           "--adapter-path", out, "--seed", str(a.chunk)]
    if a.chunk > 1:
        cmd += ["--resume-adapter-file", prev]
    begin = time.perf_counter()
    # A new process group, so a timeout stops /usr/bin/time AND the training process under it.
    proc = subprocess.Popen(["/usr/bin/time", "-l"] + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=a.timeout_minutes * 60)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            stdout, stderr = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
        exit_code = "timeout"
    log = (stdout or "") + "\n" + (stderr or "")
    seconds = time.perf_counter() - begin
    with open(os.path.join(out, "train.log"), "x", encoding="utf-8") as f:
        f.write(log)
    rss = re.findall(r"(\d+)\s+maximum resident set size", log)
    import mlx.core as mx  # noqa: E402
    import mlx_lm  # noqa: E402
    adapter = os.path.join(out, "adapters.safetensors")
    receipt = {"chunk": a.chunk, "iters": a.iters, "exit": exit_code, "seconds": round(seconds, 1),
               "maxRssGB": round(int(rss[-1]) / 1e9, 3) if rss else None, **summarize_metrics(metrics),
               "rows": {"orderStart": start, "count": len(rows), "trainLines": len(lines),
                        "sha256": sha(os.path.join(data_dir, "train.jsonl"))},
               "command": cmd, "mlx": mx.__version__, "mlxLm": mlx_lm.__version__,
               "resumedFrom": prev if a.chunk > 1 else None,
               "adapterSha256": sha(adapter) if os.path.exists(adapter) else None,
               "configSha256": sha(a.config)}
    with open(os.path.join(out, "receipt.json"), "x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print(json.dumps({k: receipt[k] for k in ("chunk", "exit", "seconds", "trainLoss", "valLoss", "tokensPerSecond",
                                             "peakMemoryGB", "maxRssGB")}), file=sys.stderr)
    return 0 if exit_code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
