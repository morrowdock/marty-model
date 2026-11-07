#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check, for one model's chat template, that training and evaluation see the same prompt.

mlx-lm renders each training row with the tokenizer's chat template (default options)
and masks the loss up to the length of the rendered prompt. run_eval.py builds its
prompt with enable_thinking=False. This script checks every row of a split:

  * prefix: the full training render starts with the evaluation prompt tokens;
  * offset: mlx-lm's mask length minus the evaluation prompt length (0 means the loss
    starts exactly at the answer; > 0 means some template tokens after the prompt are
    also masked; < 0 means some template tokens are trained on);
  * the longest full render, against max_seq_length.

  "$VENV/bin/python" stage1/check_template.py --model MODEL_DIR --data DATA_DIR \\
      --split train --receipt RECEIPT.json

Exit 1 if any row fails the prefix check. Tokenizer only (no model weights loaded).
"""

import argparse
import json
import os
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--receipt", required=True)
    a = ap.parse_args(argv)
    if os.path.exists(a.receipt):
        ap.error(f"{a.receipt} exists; refusing to overwrite")

    from transformers import AutoTokenizer  # noqa: E402  (Stage 1 virtual environment)

    tok = AutoTokenizer.from_pretrained(a.model)
    bad, offsets, longest, rows = [], {}, 0, 0
    with open(os.path.join(a.data, a.split + ".jsonl"), encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            m = json.loads(line)["messages"]
            full = tok.apply_chat_template(m, return_dict=False)
            mask = tok.apply_chat_template(m[:-1], add_generation_prompt=True, return_dict=False)
            prompt = tok.apply_chat_template(m[:-1], add_generation_prompt=True, enable_thinking=False,
                                             return_dict=False)
            rows += 1
            longest = max(longest, len(full))
            if full[:len(prompt)] != prompt:
                bad.append(number)
            delta = len(mask) - len(prompt)
            offsets[delta] = offsets.get(delta, 0) + 1
    example = json.loads(open(os.path.join(a.data, a.split + ".jsonl"), encoding="utf-8").readline())["messages"]
    receipt = {"model": os.path.abspath(a.model), "split": a.split, "rows": rows, "prefixFailures": len(bad),
               "firstFailures": bad[:10], "maskOffsetMinusPrompt": {str(k): v for k, v in sorted(offsets.items())},
               "longestTokens": longest,
               "evalPromptTail": tok.decode(tok.apply_chat_template(example[:-1], add_generation_prompt=True,
                                                                    enable_thinking=False, return_dict=False)[-8:])}
    with open(a.receipt, "x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print(json.dumps(receipt, sort_keys=True), file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
