"""RoPE Neural Verifier Inference Engine.

Integrates the trained Rotary Position Embedding (RoPE) Transformer model with
Tathya's real-time document grounding pipeline.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch

from app.core.config import settings
from app.core.rope_model import TathyaRoPEVerifier
from app.core.train_rope import DocumentTokenizer

logger = logging.getLogger("tathya.rope_inference")

# Global singleton cache for the loaded model
_MODEL_INSTANCE: Optional[TathyaRoPEVerifier] = None
_TOKENIZER_INSTANCE: Optional[DocumentTokenizer] = None
_DEVICE: Optional[torch.device] = None
_CHECKPOINT_ID = None

def invalidate_rope_model():
    global _MODEL_INSTANCE, _TOKENIZER_INSTANCE, _CHECKPOINT_ID
    _MODEL_INSTANCE = None
    _TOKENIZER_INSTANCE = None
    _CHECKPOINT_ID = None

LABEL_MAP = {
    0: "supported",
    1: "contradicted",
    2: "unsupported",
}


def load_rope_model(checkpoint_path: Optional[str] = None) -> Tuple[TathyaRoPEVerifier, DocumentTokenizer, torch.device]:
    """Loads and caches the RoPE fact verification model."""
    global _MODEL_INSTANCE, _TOKENIZER_INSTANCE, _DEVICE, _CHECKPOINT_ID

    checkpoint_path = checkpoint_path or os.path.join(settings.MODEL_ARTIFACT_DIR, "rope_verifier_best.pt")
    if not os.path.isfile(checkpoint_path):
        raise RuntimeError("Trained model checkpoint is missing")
    checkpoint_id = (str(Path(checkpoint_path).resolve()), os.stat(checkpoint_path).st_mtime_ns)
    if _MODEL_INSTANCE is not None and _TOKENIZER_INSTANCE is not None and _CHECKPOINT_ID == checkpoint_id:
        return _MODEL_INSTANCE, _TOKENIZER_INSTANCE, _DEVICE or torch.device("cpu")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _DEVICE = device

    tokenizer = DocumentTokenizer(max_length=512)

    if checkpoint_path is None:
        checkpoint_path = os.path.join(settings.MODEL_ARTIFACT_DIR, "rope_verifier_best.pt")

    model = TathyaRoPEVerifier(
        vocab_size=tokenizer.vocab_size,
        hidden_dim=256,
        num_layers=4,
        num_heads=4,
        ffn_dim=1024,
        max_seq_len=512,
        num_classes=3,
        dropout=0.0,
    ).to(device)

    if os.path.exists(checkpoint_path):
        try:
            checkpoint = torch.load(checkpoint_path, map_location=device)
            model.load_state_dict(checkpoint["model_state_dict"])
            logger.info(f"Loaded trained RoPE model weights from {checkpoint_path}")
        except Exception as e:
            raise RuntimeError("Trained model checkpoint could not be loaded") from e
    else:
        raise RuntimeError("Trained model checkpoint is missing")

    _CHECKPOINT_ID = checkpoint_id
    model.eval()
    _MODEL_INSTANCE = model
    _TOKENIZER_INSTANCE = tokenizer
    return model, tokenizer, device


def verify_with_rope(
    claim_text: str,
    evidence_text: str,
    checkpoint_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Verifies a claim against evidence using the RoPE Neural Network.

    Returns:
        {
            "status": "supported" | "contradicted" | "unsupported",
            "confidence": float,
            "risk_score": float,
            "probabilities": {"supported": float, "contradicted": float, "unsupported": float},
            "reason": str
        }
    """
    model, tokenizer, device = load_rope_model(checkpoint_path)

    tokens, mask = tokenizer.encode(claim_text, evidence_text)
    input_ids = torch.tensor([tokens], dtype=torch.long).to(device)
    attention_mask = torch.tensor([mask], dtype=torch.long).to(device)

    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        probs = outputs["probabilities"][0].cpu().numpy()
        pred_idx = int(outputs["predictions"][0].item())
        confidence = float(outputs["confidence"][0].item())
        risk_score = float(outputs["risk_score"][0].item())

    status = LABEL_MAP.get(pred_idx, "unsupported")

    reason_map = {
        "supported": f"Verified with high semantic consistency ({confidence*100:.1f}%) via RoPE attention matrix.",
        "contradicted": f"Contradiction detected against source text with {confidence*100:.1f}% certainty.",
        "unsupported": "Insufficient direct grounding found in the document context.",
    }

    return {
        "status": status,
        "confidence": round(confidence, 4),
        "risk_score": round(risk_score, 4),
        "probabilities": {
            "supported": round(float(probs[0]), 4),
            "contradicted": round(float(probs[1]), 4),
            "unsupported": round(float(probs[2]), 4),
        },
        "reason": reason_map.get(status, "Grounding verification completed."),
    }
