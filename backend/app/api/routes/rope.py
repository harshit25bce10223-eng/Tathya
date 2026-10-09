"""API endpoints for RoPE Model Training, Status, and Inference."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from app.api.deps import AdminDep, CurrentUser
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.rope_inference import verify_with_rope
from app.core.train_rope import train_rope_model

router = APIRouter(prefix="/rope", tags=["rope-model"])

_TRAINING_LOCK = threading.Lock()
_TRAINING_STATE = {
    "is_training": False,
    "last_accuracy": None,
    "last_checkpoint": None,
    "error": None,
}


class RoPEVerifyRequest(BaseModel):
    claim: str = Field(..., min_length=1, max_length=10000, description="Fact/claim text to verify")
    evidence: str = Field(..., min_length=1, max_length=100000, description="Source document or reference clause text")


class RoPETrainRequest(BaseModel):
    epochs: int = Field(default=15, ge=1, le=100)
    batch_size: int = Field(default=8, ge=2, le=64)
    lr: float = Field(default=4e-4, ge=1e-5, le=1e-2)


def _background_train(epochs: int, batch_size: int, lr: float):
    global _TRAINING_STATE
    try:
        res = train_rope_model(epochs=epochs, batch_size=batch_size, lr=lr, artifact_dir=settings.MODEL_ARTIFACT_DIR)
        from app.core.rope_inference import invalidate_rope_model
        invalidate_rope_model()
        with _TRAINING_LOCK:
            _TRAINING_STATE["last_accuracy"] = res.get("best_val_accuracy")
            _TRAINING_STATE["last_checkpoint"] = res.get("checkpoint")
    except Exception:
        with _TRAINING_LOCK:
            _TRAINING_STATE["error"] = "Training failed. Check the training data and server logs."
    finally:
        with _TRAINING_LOCK:
            _TRAINING_STATE["is_training"] = False


@router.post("/train", response_model=Dict[str, Any])
def trigger_rope_training(payload: RoPETrainRequest, background_tasks: BackgroundTasks, admin: AdminDep):
    """Trigger live training of RoPE fact verification model."""
    with _TRAINING_LOCK:
        if _TRAINING_STATE["is_training"]:
            raise HTTPException(409, "Model training is already running.")
        _TRAINING_STATE["is_training"] = True
        _TRAINING_STATE["error"] = None
    background_tasks.add_task(_background_train, payload.epochs, payload.batch_size, payload.lr)
    return {
        "status": "started",
        "message": f"RoPE Model training launched ({payload.epochs} epochs).",
        "config": payload.model_dump(),
    }


@router.get("/metrics", response_model=Dict[str, Any])
def get_training_metrics(current_user: CurrentUser):
    """Retrieve current training metrics, loss curve history, confusion matrix, and gating decision."""
    metrics_file = os.path.join(settings.MODEL_ARTIFACT_DIR, "training_metrics.json")
    results_file = os.path.join(Path(__file__).resolve().parent.parent.parent.parent, "training", "results.json")

    metrics_data = None
    if os.path.exists(metrics_file):
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics_data = json.load(f)
        except Exception:
            metrics_data = None

    prompt_b_results = None
    if os.path.exists(results_file):
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                prompt_b_results = json.load(f)
        except Exception:
            prompt_b_results = None

    return {
        "is_training": _TRAINING_STATE["is_training"],
        "state": _TRAINING_STATE,
        "metrics": metrics_data,
        "gating_results": prompt_b_results,
    }


@router.post("/verify", response_model=Dict[str, Any])
def run_rope_verification(payload: RoPEVerifyRequest, current_user: CurrentUser):
    """Run real-time high-accuracy verification on a claim vs evidence pair."""
    try:
        result = verify_with_rope(claim_text=payload.claim, evidence_text=payload.evidence)
        return {
            "success": True,
            "claim": payload.claim,
            "evidence": payload.evidence,
            "verification": result,
        }
    except RuntimeError as e:
        raise HTTPException(503, "The trained verification model is unavailable. Train or restore a valid checkpoint.") from e
