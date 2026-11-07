#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run ONE bounded QLoRA training chunk with mlx-lm and write a receipt.

Each chunk is a separate heavy-gate job (the gate is shared; do not hold it for hours):

  zsh .../mini-heavy-gate.sh model "$VENV/bin/python" stage1/train_chunk.py \\
      --model "$STAGE/models/granite-4.2-3b-q4" --data "$STAGE/data/v1" \\
      --config stage1/lora.yaml --chunk 1 --iters 100 \\
      --adapters "$STAGE/adapters/granite" [--keep-free-gb 3]

Chunk k writes ADAPTERS/chunk-k/ and resumes from ADAPTERS/chunk-(k-1)/ when k > 1.
The data order is shuffled with seed = k, so chunks do not repeat the same examples.
The receipt (ADAPTERS/chunk-k/receipt.json) records the command, versions, seconds,
peak memory and the last reported train/validation loss, and the adapter SHA-256.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_log(text):
    """Last train loss, last validation loss, last peak memory and tokens/s from mlx-lm output."""
    def last(pattern):
        found = re.findall(pattern, text)
        return float(found[-1]) if found else None
    return {"trainLoss": last(r"Train loss ([0-9.]+)"), "valLoss": last(r"Val loss ([0-9.]+)"),
            "peakMemoryGB": last(r"Peak mem ([0-9.]+) GB"), "tokensPerSecond": last(r"Tokens/sec ([0-9.]+)"),
            "trainedTokens": last(r"Trained Tokens (\d+)")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--chunk", type=int, required=True)
    ap.add_argument("--iters", type=int, required=True)
    ap.add_argument("--adapters", required=True)
    ap.add_argument("--keep-free-gb", type=float, default=3.0)
    a = ap.parse_args(argv)
    if a.chunk < 1 or not 1 <= a.iters <= 400:
        ap.error("--chunk must be >= 1 and --iters 1..400 (keep each gate job short)")
    out = os.path.join(a.adapters, f"chunk-{a.chunk}")
    prev = os.path.join(a.adapters, f"chunk-{a.chunk - 1}", "adapters.safetensors")
    if os.path.exists(out):
        ap.error(f"{out} exists; refusing to overwrite")
    if a.chunk > 1 and not os.path.exists(prev):
        ap.error(f"missing previous chunk {prev}")
    os.makedirs(a.adapters, exist_ok=True)
    if shutil.disk_usage(a.adapters).free < a.keep_free_gb * 1e9:
        raise SystemExit(f"less than {a.keep_free_gb} GB free; not starting")

    cmd = [sys.executable, "-m", "mlx_lm", "lora", "--model", a.model, "--train", "--data", a.data,
           "-c", a.config, "--iters", str(a.iters), "--adapter-path", out, "--seed", str(a.chunk)]
    if a.chunk > 1:
        cmd += ["--resume-adapter-file", prev]
    start = time.perf_counter()
    done = subprocess.run(["/usr/bin/time", "-l"] + cmd, capture_output=True, text=True, check=False)
    seconds = time.perf_counter() - start
    log = done.stdout + "\n" + done.stderr
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "train.log"), "x", encoding="utf-8") as f:
        f.write(log)
    rss = re.findall(r"(\d+)\s+maximum resident set size", done.stderr)
    import mlx.core as mx  # noqa: E402
    import mlx_lm  # noqa: E402
    adapter = os.path.join(out, "adapters.safetensors")
    receipt = {"chunk": a.chunk, "iters": a.iters, "exit": done.returncode, "seconds": round(seconds, 1),
               "maxRssGB": round(int(rss[-1]) / 1e9, 3) if rss else None, **parse_log(log),
               "command": cmd, "mlx": mx.__version__, "mlxLm": mlx_lm.__version__,
               "resumedFrom": prev if a.chunk > 1 else None,
               "adapterSha256": sha(adapter) if os.path.exists(adapter) else None,
               "configSha256": sha(a.config)}
    with open(os.path.join(out, "receipt.json"), "x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print(json.dumps({k: receipt[k] for k in ("chunk", "exit", "seconds", "trainLoss", "valLoss", "peakMemoryGB",
                                             "maxRssGB")}), file=sys.stderr)
    return done.returncode


if __name__ == "__main__":
    sys.exit(main())
