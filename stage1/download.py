#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Download one pinned model revision into a folder OUTSIDE the repository, after a
disk check, and verify every large file's SHA-256 against the Hub's LFS record.

Run with the Stage 1 virtual environment's Python (huggingface_hub comes with mlx-lm):

  "$VENV/bin/python" stage1/download.py --repo ibm-granite/granite-4.2-3b-q4-mlx \\
      --revision 0c6f39b1827afd5eb2c1c3b13751929857434953 --dest "$STAGE/models/granite-4.2-3b-q4" \\
      --receipt "$STAGE/receipts/download-granite.json" [--keep-free-gb 4]

It refuses to start if, after the download, less than --keep-free-gb would stay free.
It writes a receipt: repo, revision, licence tag, file names, sizes, SHA-256, seconds.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--revision", required=True, help="full commit SHA on the Hub")
    ap.add_argument("--dest", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--keep-free-gb", type=float, default=4.0)
    a = ap.parse_args(argv)
    if len(a.revision) != 40:
        ap.error("--revision must be a full 40-character commit SHA")
    for path in (a.dest, a.receipt):
        if os.path.exists(path):
            ap.error(f"{path} exists; refusing to overwrite")

    from huggingface_hub import HfApi, snapshot_download  # noqa: E402

    info = HfApi().model_info(a.repo, revision=a.revision, files_metadata=True)
    if info.sha != a.revision:
        raise SystemExit(f"Hub returned revision {info.sha}, not {a.revision}")
    files = [(s.rfilename, s.size or 0, (s.lfs or {}).get("sha256") if isinstance(s.lfs, dict)
              else getattr(s.lfs, "sha256", None)) for s in info.siblings]
    total = sum(size for _, size, _ in files)
    parent = os.path.dirname(os.path.abspath(a.dest))
    os.makedirs(parent, exist_ok=True)
    free = shutil.disk_usage(parent).free
    if free - total < a.keep_free_gb * 1e9:
        raise SystemExit(f"not enough disk: {free / 1e9:.1f} GB free, download {total / 1e9:.2f} GB, "
                         f"must keep {a.keep_free_gb} GB free")
    card = info.card_data.to_dict() if info.card_data else {}
    start = time.perf_counter()
    snapshot_download(a.repo, revision=a.revision, local_dir=a.dest)
    seconds = time.perf_counter() - start

    out = []
    for name, size, lfs_sha in sorted(files):
        path = os.path.join(a.dest, name)
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        digest = h.hexdigest()
        if lfs_sha and digest != lfs_sha:
            raise SystemExit(f"{name}: sha256 {digest} does not match the Hub LFS record {lfs_sha}")
        if os.path.getsize(path) != size and size:
            raise SystemExit(f"{name}: size {os.path.getsize(path)} != {size}")
        out.append({"file": name, "bytes": os.path.getsize(path), "sha256": digest, "lfsVerified": bool(lfs_sha)})
    receipt = {"repo": a.repo, "revision": a.revision, "licence": card.get("license"),
               "licenceLink": card.get("license_link"), "baseModel": card.get("base_model"),
               "gated": getattr(info, "gated", None), "files": out, "totalBytes": sum(f["bytes"] for f in out),
               "seconds": round(seconds, 1), "freeBytesAfter": shutil.disk_usage(parent).free}
    os.makedirs(os.path.dirname(os.path.abspath(a.receipt)), exist_ok=True)
    with open(a.receipt, "x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print(json.dumps({k: receipt[k] for k in ("repo", "revision", "licence", "totalBytes", "seconds")}),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
