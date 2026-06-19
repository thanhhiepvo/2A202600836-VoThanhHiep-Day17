"""Fuzzy decontamination for preference pairs — bonus prototype.

Exact-match decontamination (dataset.decontaminate) misses paraphrased prompts.
Production pipelines add character n-gram overlap or embedding similarity so a
reworded eval question cannot leak into DPO training data.

This module uses character 13-grams + Jaccard similarity — cheap, zero-key, and
works on Vietnamese without a tokenizer (tones and word boundaries vary).
"""
from __future__ import annotations

import unicodedata

from .dataset import _norm, decontaminate


def _fuzzy_norm(text: str) -> str:
    return _norm(unicodedata.normalize("NFC", text or ""))


def char_ngrams(text: str, n: int = 13) -> set[str]:
    """Character n-grams after normalization. Robust to Vietnamese paraphrasing."""
    s = _fuzzy_norm(text)
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_near_duplicate(prompt: str, eval_input: str, *, n: int = 13, threshold: float = 0.35) -> bool:
    """True when prompt and eval_input share enough character n-grams."""
    return jaccard(char_ngrams(prompt, n), char_ngrams(eval_input, n)) >= threshold


def fuzzy_decontaminate(
    pairs: list[dict],
    eval_set: list[dict],
    *,
    n: int = 13,
    threshold: float = 0.35,
) -> list[dict]:
    """Drop pairs whose prompt is an exact OR near-duplicate of any eval input."""
    clean = []
    for p in pairs:
        if any(is_near_duplicate(p["prompt"], e["input"], n=n, threshold=threshold) for e in eval_set):
            continue
        clean.append(p)
    return clean


def compare_methods(pairs: list[dict], eval_set: list[dict]) -> dict:
    """Side-by-side: exact vs fuzzy decontamination (for the bonus demo)."""
    exact = decontaminate(pairs, eval_set)
    fuzzy = fuzzy_decontaminate(pairs, eval_set)
    exact_dropped = {p["prompt"] for p in pairs} - {p["prompt"] for p in exact}
    fuzzy_dropped = {p["prompt"] for p in pairs} - {p["prompt"] for p in fuzzy}
    return {
        "pairs_in": len(pairs),
        "exact_clean": len(exact),
        "fuzzy_clean": len(fuzzy),
        "exact_dropped": sorted(exact_dropped),
        "fuzzy_dropped": sorted(fuzzy_dropped),
        "fuzzy_extra_dropped": sorted(fuzzy_dropped - exact_dropped),
    }
