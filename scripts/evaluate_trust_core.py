"""Reproducible synthetic smoke evaluation; never claims production calibration."""

from __future__ import annotations
import argparse
import hashlib
import json
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.source_verification import compare_quote, values
from app.core.retrieval import _bm25_ranks
from app.core.z3_engine import solve_constraints


def metrics(rows):
    tp = fp = fn = tn = abstentions = correct = 0
    for row in rows:
        expected, actual = row["expected"], row["actual"]
        correct += expected == actual
        positive = expected in ("contradicted", "unsupported")
        detected = actual in ("contradicted", "unsupported")
        if positive and detected:
            tp += 1
        elif positive:
            fn += 1
        elif detected:
            fp += 1
        elif actual == "supported":
            tn += 1
        if actual == "uncertain":
            abstentions += 1
        if expected == "uncertain":
            # Ambiguous ground truth is included in status accuracy, not binary detection.
            if detected:
                fp -= 1
            elif actual == "supported":
                tn -= 1
    times = sorted(r["latency_ms"] for r in rows)
    return {
        "claims": len(rows),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "abstentions": abstentions,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
        "exact_status_accuracy": correct / len(rows) if rows else None,
        "latency_mean_ms": sum(times) / len(times) if times else None,
        "latency_p95_ms": times[min(len(times) - 1, int(len(times) * 0.95))]
        if times
        else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "evaluation/synthetic-v1.jsonl"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/system-repair-validation/evaluation.json",
    )
    parser.add_argument(
        "--live-judge",
        action="store_true",
        help="Explicitly allow configured provider calls on synthetic fixtures.",
    )
    args = parser.parse_args()
    raw = args.dataset.read_bytes()
    cases = [
        json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()
    ]
    families = defaultdict(set)
    for c in cases:
        families[c["family"]].add(c["split"])
    if any(len(v) > 1 for v in families.values()):
        raise ValueError("A document family leaked across dataset splits.")
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate fixture IDs.")
    report = {
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "label_origin": "synthetic author-declared",
        "scope": "component smoke evaluation; not full pipeline, unseen human benchmark or production calibration",
        "modes": {},
    }
    for mode in [
        "retrieval_only",
        "retrieval_rules",
        "retrieval_rules_judge",
        "retrieval_rules_z3",
    ]:
        if mode.endswith("judge") and not args.live_judge:
            report["modes"][mode] = {
                "availability": "not_run",
                "reason": "Live provider evaluation requires --live-judge; no fabricated substitute.",
            }
            continue
        rows = []
        for c in cases:
            start = time.perf_counter()
            actual = "uncertain"
            proof = None
            error = None
            try:
                ranked = _bm25_ranks(c["claim"], c["sources"]) if c["sources"] else []
                quotes = [c["sources"][i] for i in ranked[:3]]
                if mode != "retrieval_only":
                    decisions = {
                        v
                        for q in quotes
                        if (v := compare_quote(c["claim"], q)) is not None
                    }
                    actual = (
                        next(iter(decisions)) if len(decisions) == 1 else "uncertain"
                    )
                if mode.endswith("judge") and actual == "uncertain":
                    from app.core.judge import verify_with_judge

                    evidence = [
                        {
                            "id": uuid.uuid5(uuid.NAMESPACE_URL, c["id"] + str(i)),
                            "quote": q,
                            "location": f"synthetic:{c['id']}:{i}",
                            "support_type": "candidate",
                            "score": 0.0,
                        }
                        for i, q in enumerate(quotes)
                    ]
                    actual = verify_with_judge(
                        c["claim"], c["category"], evidence
                    ).status
                if mode.endswith("z3") and actual != "uncertain" and len(quotes) == 1:
                    cv, sv = values(c["claim"]), values(quotes[0])
                    keys = [
                        k
                        for k in set(cv) & set(sv)
                        if k != "date" and len(cv[k]) == len(sv[k]) == 1
                    ]
                    if keys:
                        k = sorted(keys)[0]
                        proof = solve_constraints(
                            numeric_constraints=[
                                {
                                    "variable": "business_value",
                                    "operator": "eq",
                                    "value": str(cv[k][0]),
                                },
                                {
                                    "variable": "business_value",
                                    "operator": "eq",
                                    "value": str(sv[k][0]),
                                },
                            ],
                            max_timeout_seconds=2,
                        )
            except Exception as exc:
                error = type(exc).__name__
                actual = "uncertain"
            rows.append(
                {
                    "id": c["id"],
                    "split": c["split"],
                    "category": c["category"],
                    "expected": c["expected"],
                    "actual": actual,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 3),
                    "retrieved_count": len(ranked),
                    "proof": proof,
                    "error": error,
                }
            )
        report["modes"][mode] = {
            "availability": "executed",
            "overall": metrics(rows),
            "by_category": {
                category: metrics([r for r in rows if r["category"] == category])
                for category in sorted({r["category"] for r in rows})
            },
            "by_split": {
                split: metrics([r for r in rows if r["split"] == split])
                for split in sorted({r["split"] for r in rows})
            },
            "rows": rows,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {m: r.get("overall", r.get("reason")) for m, r in report["modes"].items()},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
