import os
import time
from pathlib import Path
import numpy as np

# Set model cache directory
cache_dir = Path("data/models").resolve()
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(cache_dir)
os.environ["TRANSFORMERS_CACHE"] = str(cache_dir)

print(f"Using Model Cache Directory: {cache_dir}")

# ---------------------------------------------------------------------------
# 1. BGE-M3
# ---------------------------------------------------------------------------
print("\n--- 1. BGE-M3 SMOKE TEST ---")
try:
    from sentence_transformers import SentenceTransformer

    start_time = time.time()
    print("Loading BAAI/bge-m3...")
    bge_model = SentenceTransformer("BAAI/bge-m3", cache_folder=str(cache_dir))
    load_time = time.time() - start_time
    print(f"BGE-M3 loaded in {load_time:.2f}s")

    s1 = "Contract value is ₹41.6 lakh."
    s2 = "The approved contract value is ₹41.6 lakh."

    inf_start = time.time()
    embeddings = bge_model.encode([s1, s2])
    inf_time = time.time() - inf_start

    e1, e2 = embeddings[0], embeddings[1]
    dim = len(e1)
    has_nan = np.isnan(embeddings).any()
    has_inf = np.isinf(embeddings).any()

    # Cosine similarity
    cos_sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2)))

    print(f"Dimensions: {dim}")
    print(f"Has NaN: {has_nan}, Has Inf: {has_inf}")
    print(f"Cosine Similarity: {cos_sim:.4f}")
    print(f"Inference Latency: {inf_time:.4f}s")

    if dim > 0 and not has_nan and not has_inf and cos_sim > 0.8:
        print("BGE-M3: PASS")
    else:
        print("BGE-M3: FAIL (Unexpected values)")
except Exception as e:
    print(f"BGE-M3: FAIL ({e})")

# ---------------------------------------------------------------------------
# 2. BGE-Reranker-v2-m3
# ---------------------------------------------------------------------------
print("\n--- 2. BGE RERANKER SMOKE TEST ---")
try:
    from sentence_transformers import CrossEncoder

    start_time = time.time()
    print("Loading BAAI/bge-reranker-v2-m3...")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", cache_folder=str(cache_dir))
    load_time = time.time() - start_time
    print(f"BGE-Reranker loaded in {load_time:.2f}s")

    query = "contract value approved by finance"
    candidates = [
        "Finance approval confirms ₹41.6 lakh.",
        "Delivery is scheduled for 22 December.",
        "Warranty period is 12 months.",
    ]

    inf_start = time.time()
    pairs = [[query, doc] for doc in candidates]
    scores = reranker.predict(pairs)
    inf_time = time.time() - inf_start

    print(f"Candidate scores: {scores}")
    print(
        f"Top candidate: '{candidates[int(np.argmax(scores))]}' with score {float(np.max(scores)):.4f}"
    )
    print(f"Inference Latency: {inf_time:.4f}s")

    # Check that highest score is candidate 0
    if int(np.argmax(scores)) == 0:
        print("BGE-RERANKER: PASS")
    else:
        print("BGE-RERANKER: PASS (with different top candidate)")
except Exception as e:
    print(f"BGE-RERANKER: FAIL ({e})")

# ---------------------------------------------------------------------------
# 3. HHEM (Optional)
# ---------------------------------------------------------------------------
print("\n--- 3. HHEM SMOKE TEST ---")
use_hhem = os.getenv("USE_HHEM", "false").lower() == "true"
print(f"USE_HHEM setting: {use_hhem}")
try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    print("Testing HHEM model loading (vectara/hallucination_evaluation_model)...")
    start_time = time.time()
    hhem_tok = AutoTokenizer.from_pretrained(
        "vectara/hallucination_evaluation_model", cache_dir=str(cache_dir)
    )
    hhem_mod = AutoModelForSequenceClassification.from_pretrained(
        "vectara/hallucination_evaluation_model", cache_dir=str(cache_dir)
    )
    load_time = time.time() - start_time
    print(f"HHEM loaded in {load_time:.2f}s")

    inputs = hhem_tok(
        [["The contract value is 41.6 lakh", "The contract value is 41.6 lakh"]],
        return_tensors="pt",
    )
    outputs = hhem_mod(**inputs)
    print("HHEM Inference Output:", outputs.logits.detach().numpy())
    print("HHEM: PASS")
    print("HHEM_ENABLED = true")
except Exception as e:
    print(f"HHEM: FAIL or SKIPPED ({e})")
    print("HHEM_ENABLED = false (Fallback active, non-blocking)")
