"""
Phase 0 — Model downloader for Tathya.
Downloads BGE-M3, BGE-Reranker-v2-m3, and HHEM using huggingface_hub
snapshot_download (no hf-xet, standard HTTP).

Run from project root:
    .venv/Scripts/python.exe scripts/download_models.py
"""

import os
import sys
import time

# Use the local data/models cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "models")
os.makedirs(CACHE_DIR, exist_ok=True)

MODELS = [
    {
        "repo_id": "BAAI/bge-m3",
        "label": "BGE-M3 (embedding)",
        "ignore_patterns": ["*.gguf", "onnx/*", "onnx_fp16/*"],
    },
    {
        "repo_id": "BAAI/bge-reranker-v2-m3",
        "label": "BGE-Reranker-v2-m3",
        "ignore_patterns": ["*.gguf"],
    },
    {
        "repo_id": "vectara/hallucination_evaluation_model",
        "label": "HHEM v2.1",
        "ignore_patterns": [],
    },
]


def format_bytes(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def download_model(repo_id: str, label: str, ignore_patterns: list[str]) -> bool:
    print(f"\n{'=' * 60}")
    print(f"Downloading: {label}")
    print(f"  repo_id : {repo_id}")
    print(f"  cache   : {CACHE_DIR}")
    print(f"{'=' * 60}")

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("ERROR: huggingface_hub not installed")
        return False

    # Disable hf-xet if somehow still present
    os.environ["HF_HUB_DISABLE_XET"] = "1"

    t0 = time.time()
    try:
        path = snapshot_download(
            repo_id=repo_id,
            cache_dir=CACHE_DIR,
            ignore_patterns=ignore_patterns if ignore_patterns else None,
        )
        elapsed = time.time() - t0
        # Report total size
        total = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, files in os.walk(path)
            for f in files
        )
        print(f"  [OK] Downloaded to: {path}")
        print(f"  [OK] Total size   : {format_bytes(total)}")
        print(f"  [OK] Time elapsed : {elapsed:.1f}s")
        return True
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        return False


def smoke_test_bge_m3() -> bool:
    print("\n--- Smoke test: BGE-M3 load ---")
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            "BAAI/bge-m3",
            cache_folder=CACHE_DIR,
            device="cpu",
        )
        vecs = model.encode(["Tathya fact-checks AI documents."])
        print(f"  [OK] BGE-M3 encode OK, vector dim={len(vecs[0])}")
        return True
    except Exception as e:
        print(f"  [FAIL] BGE-M3 smoke test FAILED: {e}")
        return False


def smoke_test_reranker() -> bool:
    print("\n--- Smoke test: BGE-Reranker load ---")
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(
            "BAAI/bge-reranker-v2-m3",
            max_length=512,
        )
        score = model.predict([("query", "document text here")])
        print(f"  [OK] BGE-Reranker predict OK, score={score}")
        return True
    except Exception as e:
        print(f"  [FAIL] BGE-Reranker smoke test FAILED: {e}")
        return False


def smoke_test_hhem() -> bool:
    print("\n--- Smoke test: HHEM load ---")
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder("vectara/hallucination_evaluation_model")
        scores = model.predict(
            [("The capital of France is Paris.", "Paris is the capital of France.")]
        )
        print(f"  [OK] HHEM predict OK, score={scores}")
        return True
    except Exception as e:
        print(f"  [FAIL] HHEM smoke test FAILED: {e}")
        return False


if __name__ == "__main__":
    results = {}
    for m in MODELS:
        ok = download_model(m["repo_id"], m["label"], m["ignore_patterns"])
        results[m["label"]] = "DOWNLOADED" if ok else "FAILED"

    print("\n\n" + "=" * 60)
    print("DOWNLOAD RESULTS")
    print("=" * 60)
    for label, status in results.items():
        icon = "[OK]" if status == "DOWNLOADED" else "[FAIL]"
        print(f"  {icon} {label}: {status}")

    # Run smoke tests only if downloads passed
    print("\n" + "=" * 60)
    print("SMOKE TESTS")
    print("=" * 60)
    smoke_results = {}

    if results.get("BGE-M3 (embedding)") == "DOWNLOADED":
        smoke_results["BGE-M3"] = "PASS" if smoke_test_bge_m3() else "FAIL"
    else:
        smoke_results["BGE-M3"] = "SKIPPED (download failed)"

    if results.get("BGE-Reranker-v2-m3") == "DOWNLOADED":
        smoke_results["BGE-Reranker"] = "PASS" if smoke_test_reranker() else "FAIL"
    else:
        smoke_results["BGE-Reranker"] = "SKIPPED (download failed)"

    if results.get("HHEM v2.1") == "DOWNLOADED":
        smoke_results["HHEM"] = "PASS" if smoke_test_hhem() else "FAIL"
    else:
        smoke_results["HHEM"] = "SKIPPED (download failed)"

    print("\n" + "=" * 60)
    print("SMOKE TEST RESULTS")
    print("=" * 60)
    for label, status in smoke_results.items():
        icon = (
            "[OK]"
            if status == "PASS"
            else ("[SKIP]" if "SKIPPED" in status else "[FAIL]")
        )
        print(f"  {icon} {label}: {status}")

    any_fail = any(s == "FAILED" for s in results.values()) or any(
        s == "FAIL" for s in smoke_results.values()
    )
    sys.exit(1 if any_fail else 0)
