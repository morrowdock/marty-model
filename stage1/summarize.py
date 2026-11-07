#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Summarise Stage 1 result chunks: python3 stage1/summarize.py RESULTS-*.jsonl"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402


def main(paths):
    results, seen, runs = [], set(), set()
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r["id"] in seen:
                    raise SystemExit(f"duplicate item {r['id']} in {path}")
                seen.add(r["id"])
                run = r.get("run", {})
                runs.add((run.get("model"), run.get("adapterSha256"), run.get("checkerSha256"), run.get("maxTokens")))
                results.append(r)
    if len(runs) > 1:
        raise SystemExit(f"these files mix {len(runs)} different runs (model, adapter, checker, max tokens); "
                         "summarise each run separately")
    print(json.dumps(harness.summarize(results), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
