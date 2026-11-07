# SPDX-License-Identifier: Apache-2.0
"""Stage 1 evaluation core (standard library only; no model code).

`evaluate_item` runs one development item through a model and the engine:

  1. ask the model with the item's user text;
  2. check the answer with `marty-solid check`;
  3. if the engine refuses it, ask again in the repair format (reason, part, the
     model's own scene), at most `max_repairs` times;
  4. score the final accepted scene against what the item asked for.

The model is any callable `generate(user_text) -> (text, info)`, where `info` holds
`seconds`, `promptTokens`, `outputTokens` and `peakMemoryGB` (as measured by the glue
code). The scores use only engine reports and exact comparisons.
"""

import json
import re
from fractions import Fraction

MAX_ANSWER_CHARS = 64 * 1024
THINK = re.compile(r"<think>.*?</think>", re.S)
OPEN_THINK = re.compile(r"<think>.*\Z", re.S)  # reasoning cut off by the token limit
FENCE = re.compile(r"^```[a-zA-Z]*\s*\n(.*?)\n?```\s*$", re.S)


def clean(text):
    """The model's answer as scene text: drop reasoning tags and one code fence, trim."""
    text = OPEN_THINK.sub("", THINK.sub("", text[:MAX_ANSWER_CHARS])).strip()
    m = FENCE.match(text)
    return (m.group(1) if m else text).strip()


PROMPT_MODES = (("training-mask", {}), ("no-thinking", {"enable_thinking": False}))


def prompt_mode(tokenizer, messages):
    """The evaluation prompt that matches training for this chat (user + assistant).

    `tokenizer` is mlx-lm's TokenizerWrapper, which training also uses. Training renders
    `messages` with the wrapper's defaults and masks the loss up to the length of
    `messages[:-1]` rendered with add_generation_prompt=True. The first mode IS that
    mask prefix; the second turns thinking off. Returns (name, kwargs, prompt token ids,
    mask offset) for the first mode whose prompt is an exact prefix of the training
    render, or (None, None, None, offset) when none is.
    """
    full = list(tokenizer.apply_chat_template(messages, return_dict=False))
    mask = list(tokenizer.apply_chat_template(messages[:-1], add_generation_prompt=True, return_dict=False))
    for name, kwargs in PROMPT_MODES:
        ids = list(tokenizer.apply_chat_template(messages[:-1], add_generation_prompt=True, return_dict=False,
                                                 **kwargs))
        if full[:len(ids)] == ids:
            return name, kwargs, ids, len(mask)
    return None, None, None, len(mask)


def repair_user(reason, part, scene_text):
    # Must match stage1/make_data.py:repair_user (the training format).
    return f"task: repair\nreason: {reason}\npart: {part}\nscene: {scene_text}"


def parsed_use(scene_text):
    """(component id, with dict) of the scene's first part, or (None, None)."""
    try:
        doc = json.loads(scene_text)
        part = doc["parts"][0]
        return part.get("use"), part.get("with")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return None, None


def correct(meta, scene_text, report):
    """Whether an ACCEPTED scene does what the item asked (engine numbers, exact compare)."""
    if not report.get("ok"):
        return False
    component, values = parsed_use(scene_text)
    if component != meta["component"] or not isinstance(values, dict):
        return False
    want = meta["want"]
    if meta["task"] == "author.ratio":
        got = (report.get("ratios") or {}).get(want["part"])
        target = Fraction(*want["ratio"])
        fixed_ok = all(values.get(k) == v for k, v in meta["with"].items()
                       if k in ("module", "width", "planets"))
        return isinstance(got, (int, float)) and not isinstance(got, bool) and \
            abs(float(target) - got) <= 1e-9 and fixed_ok
    # author.params and repair: the accepted scene must keep exactly the intended values.
    return values == meta["with"]


def evaluate_item(meta, user, generate, check, max_repairs=3):
    """Run one item; return a result dict (no exceptions for model faults)."""
    attempts = []
    prompt = user
    final_scene, final_report = None, {"ok": False}
    for attempt in range(max_repairs + 1):
        raw, info = generate(prompt)
        scene_text = clean(raw)
        report = check(scene_text)
        attempts.append({"attempt": attempt, "ok": bool(report.get("ok")), "reason": report.get("reason"),
                         "part": report.get("part"), "chars": len(scene_text), **info})
        final_scene, final_report = scene_text, report
        if report.get("ok"):
            break
        prompt = repair_user(report.get("reason"), report.get("part"), scene_text)
    accepted = bool(final_report.get("ok"))
    return {
        "id": meta["id"], "task": meta["task"], "component": meta["component"],
        "acceptedFirst": attempts[0]["ok"], "accepted": accepted, "repairs": len(attempts) - 1,
        "correct": correct(meta, final_scene, final_report) if accepted else False,
        "seconds": round(sum(a.get("seconds", 0) for a in attempts), 3),
        "outputTokens": sum(a.get("outputTokens", 0) for a in attempts),
        "peakMemoryGB": max((a.get("peakMemoryGB", 0) for a in attempts), default=0),
        "attempts": attempts, "finalScene": final_scene,
    }


def summarize(results):
    """Totals by task; percentages are of all items in that group."""
    def block(rows):
        n = len(rows)
        if not n:
            return {"n": 0}
        secs = sorted(r["attempts"][0].get("seconds", 0) for r in rows)
        toks = sum(a.get("outputTokens", 0) for r in rows for a in r["attempts"])
        gen_s = sum(a.get("seconds", 0) for r in rows for a in r["attempts"])  # includes prompt processing
        tps = [a["generationTps"] for r in rows for a in r["attempts"] if a.get("generationTps")]
        return {
            "n": n,
            "acceptedFirst": sum(r["acceptedFirst"] for r in rows),
            "acceptedWithin3": sum(r["accepted"] for r in rows),
            "correct": sum(r["correct"] for r in rows),
            "meanRepairsWhenAccepted": round(sum(r["repairs"] for r in rows if r["accepted"]) /
                                             max(1, sum(r["accepted"] for r in rows)), 3),
            "firstAnswerSecondsP50": secs[(n - 1) // 2],
            "firstAnswerSecondsP95": secs[min(n - 1, int(round(0.95 * (n - 1))))],
            "outputTokensPerSecondWall": round(toks / gen_s, 2) if gen_s else None,
            "generationTokensPerSecondMedian": sorted(tps)[(len(tps) - 1) // 2] if tps else None,
            "peakMemoryGB": max(r["peakMemoryGB"] for r in rows),
        }
    out = {"all": block(results)}
    for key in sorted({r["task"] + ":" + r["component"] for r in results}):
        out[key] = block([r for r in results if r["task"] + ":" + r["component"] == key])
    return out
