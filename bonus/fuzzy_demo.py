"""Bonus prototype: fuzzy decontamination catches paraphrased eval leakage.

    python bonus/fuzzy_demo.py

Shows one core decision from bonus/DESIGN.md: exact-match decontamination lets
reworded prompts leak into DPO pairs; character n-gram overlap catches them
without an embedding API.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.fuzzy_decontam import compare_methods, is_near_duplicate

# English eval holdout + mined preference pairs (paraphrase slips past exact match).
EVAL_EN = [
    {
        "trace_id": "eval-en-1",
        "input": "Can I return a widget I bought 10 days ago?",
        "reference": "Yes, widgets can be returned within 30 days.",
    }
]

PAIRS_EN = [
    {
        "prompt": "can i return a widget i bought 10 days ago?",  # exact duplicate
        "chosen": "Yes, within 30 days.",
        "rejected": "Sorry, I cannot help.",
    },
    {
        # Contraction paraphrase — same intent, not byte-identical after _norm.
        "prompt": "can i return a widget ive bought 10 days ago?",
        "chosen": "Yes, within 30 days.",
        "rejected": "Returns are not supported.",
    },
    {
        "prompt": "do you accept returns on opened sprockets?",
        "chosen": "No, sprockets are final sale once opened.",
        "rejected": "Sure, return anytime within 30 days.",
    },
]

# Vietnamese variant: minor wording change common in chat logs.
EVAL_VI = [
    {
        "trace_id": "eval-vi-1",
        "input": "Tôi có thể trả lại widget mua 10 ngày trước không?",
        "reference": "Có, widget có thể đổi trả trong 30 ngày.",
    }
]

PAIRS_VI = [
    {
        "prompt": "Tôi có thể trả lại widget đã mua 10 ngày trước không?",
        "chosen": "Có, trong vòng 30 ngày.",
        "rejected": "Không hỗ trợ đổi trả.",
    },
    {
        "prompt": "Sprocket đã mở seal có trả được không?",
        "chosen": "Không, sprocket final sale.",
        "rejected": "Có thể trả trong 30 ngày.",
    },
]


def _show_overlap(label: str, eval_input: str, paraphrase: str) -> None:
    dup = is_near_duplicate(paraphrase, eval_input)
    print(f"  [{label}]")
    print(f"    eval       : {eval_input}")
    print(f"    paraphrase : {paraphrase}")
    print(f"    fuzzy dup? : {dup}  (exact dup? {eval_input.lower().strip() == paraphrase.lower().strip()})")


def main() -> None:
    print("=== Bonus: fuzzy decontamination demo ===\n")

    print("1) Paraphrase detection (13-gram Jaccard >= 0.35)\n")
    _show_overlap("EN", EVAL_EN[0]["input"], PAIRS_EN[1]["prompt"])
    print()
    _show_overlap("VI", EVAL_VI[0]["input"], PAIRS_VI[0]["prompt"])

    print("\n2) Batch decontamination — English pairs\n")
    stats = compare_methods(PAIRS_EN, EVAL_EN)
    print(f"  pairs in              : {stats['pairs_in']}")
    print(f"  exact-match survivors : {stats['exact_clean']}")
    print(f"  fuzzy-match survivors : {stats['fuzzy_clean']}")
    print(f"  extra dropped (fuzzy) : {stats['fuzzy_extra_dropped']}")

    print("\n3) Batch decontamination — Vietnamese pairs\n")
    stats_vi = compare_methods(PAIRS_VI, EVAL_VI)
    print(f"  pairs in              : {stats_vi['pairs_in']}")
    print(f"  exact-match survivors : {stats_vi['exact_clean']}")
    print(f"  fuzzy-match survivors : {stats_vi['fuzzy_clean']}")
    print(f"  extra dropped (fuzzy) : {stats_vi['fuzzy_extra_dropped']}")

    print("\nConclusion: fuzzy 13-gram overlap drops paraphrased eval leaks that exact match keeps.")


if __name__ == "__main__":
    main()
