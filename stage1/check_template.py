#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check, for one model's chat template, that training and evaluation see the same prompt.

mlx-lm trains through its tokenizer wrapper: it renders each row with the wrapper's
defaults (the wrapper sets enable_thinking to whether the vocabulary has thinking
tokens) and masks the loss up to the length of the rendered prompt. This script loads
the SAME wrapper (mlx_lm.utils.load_tokenizer) and checks every row of a split with
harness.prompt_mode: which evaluation prompt form is an exact prefix of the training
render ("training-mask" = the mask prefix itself; "no-thinking" = thinking off), and
where the mask starts relative to that prompt. It also records has_thinking and the
longest render against max_seq_length.

  "$VENV/bin/python" stage1/check_template.py --model MODEL_DIR --data DATA_DIR \\
      --split train --receipt RECEIPT.json

Exit 1 if any row has no matching prompt form, or if rows need different forms.
Tokenizer only (no model weights loaded).
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

    from pathlib import Path  # noqa: E402

    from mlx_lm.utils import load_tokenizer  # noqa: E402  (Stage 1 virtual environment)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import harness  # noqa: E402

    tok = load_tokenizer(Path(a.model))
    modes, offsets, failures, longest, rows = {}, {}, [], 0, 0
    tail = None
    with open(os.path.join(a.data, a.split + ".jsonl"), encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            m = json.loads(line)["messages"]
            name, _, ids, mask_len = harness.prompt_mode(tok, m)
            rows += 1
            longest = max(longest, len(tok.apply_chat_template(m, return_dict=False)))
            modes[str(name)] = modes.get(str(name), 0) + 1
            if name is None:
                failures.append(number)
                continue
            delta = mask_len - len(ids)
            offsets[delta] = offsets.get(delta, 0) + 1
            if tail is None:
                tail = tok.decode(ids[-8:])
    receipt = {"model": os.path.abspath(a.model), "split": a.split, "rows": rows,
               "hasThinking": bool(getattr(tok, "has_thinking", False)), "promptModes": modes,
               "failures": len(failures), "firstFailures": failures[:10],
               "maskOffsetMinusPrompt": {str(k): v for k, v in sorted(offsets.items())},
               "longestTokens": longest, "evalPromptTail": tail}
    with open(a.receipt, "x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print(json.dumps(receipt, sort_keys=True), file=sys.stderr)
    return 1 if failures or len(modes) != 1 else 0


if __name__ == "__main__":
    sys.exit(main())
