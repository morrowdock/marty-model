# SPDX-License-Identifier: Apache-2.0
"""In-process mlx-lm LoRA training with a metrics callback (used by train_chunk.py).

mlx-lm 0.32's `lora.run()` replaces any callback it is given and prints a table, so
this runner builds the arguments exactly as `mlx_lm lora` does (parser, then the YAML
config, then the defaults) and calls `lora.train_model` with a callback that writes one
JSON line per report (train loss, validation loss, tokens/s, peak memory) to the file
named by --metrics.

Usage (inside the Stage 1 virtual environment):
  python stage1/lora_runner.py --metrics METRICS.jsonl <the usual mlx_lm lora arguments>
"""

import json
import os
import sys
import time
import types


def main(argv):
    if len(argv) < 2 or argv[0] != "--metrics":
        raise SystemExit("usage: lora_runner.py --metrics FILE <mlx_lm lora arguments>")
    metrics_path, argv = argv[1], argv[2:]

    import numpy as np
    import yaml
    from mlx_lm import lora
    from mlx_lm.tuner.callbacks import TrainingCallback

    os.environ["TOKENIZERS_PARALLELISM"] = "true"
    args = vars(lora.build_parser().parse_args(argv))
    if args.get("config"):
        with open(args["config"], "r") as f:
            config = yaml.load(f, lora.yaml_loader)
        for k, v in config.items():  # command-line values win, as in mlx_lm lora
            if args.get(k, None) is None:
                args[k] = v
    for k, v in lora.CONFIG_DEFAULTS.items():
        if args.get(k, None) is None:
            args[k] = v
    args = types.SimpleNamespace(**args)

    out = open(metrics_path, "x", encoding="utf-8")
    start = time.perf_counter()

    class Metrics(TrainingCallback):
        def write(self, kind, info):
            row = {"kind": kind, "seconds": round(time.perf_counter() - start, 2)}
            row.update({k: (float(v) if hasattr(v, "item") or isinstance(v, float) else v) for k, v in info.items()})
            out.write(json.dumps(row, sort_keys=True) + "\n")
            out.flush()

        def on_train_loss_report(self, train_info):
            self.write("train", train_info)

        def on_val_loss_report(self, val_info):
            self.write("val", val_info)

    np.random.seed(args.seed)
    model, tokenizer = lora.load(args.model)
    train_set, valid_set, _ = lora.load_dataset(args, tokenizer)
    lora.train_model(args, model, train_set, valid_set, Metrics())
    out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
