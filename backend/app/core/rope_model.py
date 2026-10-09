"""Rotary Position Embedding (RoPE) Neural Network for Fact & Claim Verification.

This module implements a production-grade Transformer model equipped with
Rotary Position Embeddings (RoPE) for long-context document and contract
fact verification with high precision.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. Rotary Position Embedding (RoPE) Mathematical Implementation
# ---------------------------------------------------------------------------


class RotaryEmbedding(nn.Module):
    """Rotary Position Embedding (RoPE).

    Applies rotary position transformations to Query and Key representations:
        R_{theta, m}^d = diag(R_{theta_1, m}, R_{theta_2, m}, ..., R_{theta_{d/2}, m})
    Preserves relative token distances across long document sequences.
    """

    def __init__(self, dim: int, max_seq_len: int = 8192, base: float = 10000.0):
        super().__init__()
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.base = base

        # Compute inverse frequency: theta_i = 10000^(-2(i-1)/dim)
        inv_freq = 1.0 / (self.base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

        # Precompute cosine and sine embeddings cache
        self._build_cache(max_seq_len)

    def _build_cache(self, seq_len: int):
        t = torch.arange(seq_len, dtype=torch.float32)
        freqs = torch.outer(t, self.inv_freq)  # (seq_len, dim/2)
        # Repeat to match dim: [theta_0, theta_0, theta_1, theta_1, ...]
        emb = torch.cat((freqs, freqs), dim=-1)  # (seq_len, dim)
        self.register_buffer("cos_cached", emb.cos(), persistent=False)
        self.register_buffer("sin_cached", emb.sin(), persistent=False)

    def _rotate_half(self, x: torch.Tensor) -> torch.Tensor:
        """Rotates half the hidden dimensions of the input."""
        x1 = x[..., : self.dim // 2]
        x2 = x[..., self.dim // 2 :]
        return torch.cat((-x2, x1), dim=-1)

    def forward(
        self, q: torch.Tensor, k: torch.Tensor, seq_len: int
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Applies RoPE to Q and K tensors.

        Args:
            q: Query tensor of shape (batch, num_heads, seq_len, head_dim)
            k: Key tensor of shape (batch, num_heads, seq_len, head_dim)
            seq_len: Current sequence length

        Returns:
            q_rotated, k_rotated
        """
        if seq_len > self.cos_cached.shape[0]:
            self._build_cache(seq_len)

        cos = self.cos_cached[:seq_len, :].to(q.device)
        sin = self.sin_cached[:seq_len, :].to(q.device)

        # Reshape for broadcasting with (batch, num_heads, seq_len, head_dim)
        cos = cos.unsqueeze(0).unsqueeze(1)  # (1, 1, seq_len, head_dim)
        sin = sin.unsqueeze(0).unsqueeze(1)  # (1, 1, seq_len, head_dim)

        q_rot = (q * cos) + (self._rotate_half(q) * sin)
        k_rot = (k * cos) + (self._rotate_half(k) * sin)
        return q_rot, k_rot


# ---------------------------------------------------------------------------
# 2. RoPE Multi-Head Attention Layer
# ---------------------------------------------------------------------------


class RoPEMultiHeadAttention(nn.Module):
    """Multi-Head Attention layer enhanced with Rotary Position Embeddings."""

    def __init__(self, hidden_dim: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        assert hidden_dim % num_heads == 0, "hidden_dim must be divisible by num_heads"
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads

        self.q_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.k_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.v_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.out_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)

        self.rope = RotaryEmbedding(dim=self.head_dim)
        self.dropout = nn.Dropout(dropout)
        self.scale = 1.0 / math.sqrt(self.head_dim)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (batch, seq_len, hidden_dim)
            attention_mask: Mask of shape (batch, seq_len) or (batch, 1, seq_len, seq_len)
        """
        batch_size, seq_len, _ = x.shape

        # Linear projections
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        # Reshape to (batch, num_heads, seq_len, head_dim)
        q = q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        # Apply RoPE to queries and keys
        q, k = self.rope(q, k, seq_len)

        # Scaled dot-product attention
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale

        if attention_mask is not None:
            if attention_mask.dim() == 2:
                # Shape: (batch, 1, 1, seq_len)
                mask = attention_mask.unsqueeze(1).unsqueeze(2)
            else:
                mask = attention_mask
            scores = scores.masked_fill(mask == 0, -1e9)

        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # Output projection
        context = torch.matmul(attn_weights, v)  # (batch, num_heads, seq_len, head_dim)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_dim)
        return self.out_proj(context)


# ---------------------------------------------------------------------------
# 3. Transformer Block with RoPE & SwiGLU / Feed-Forward
# ---------------------------------------------------------------------------


class TransformerBlock(nn.Module):
    """Transformer Encoder block with RoPE Attention and RMSNorm / LayerNorm."""

    def __init__(self, hidden_dim: int, num_heads: int, ffn_dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(hidden_dim, eps=1e-6)
        self.attn = RoPEMultiHeadAttention(hidden_dim, num_heads, dropout)

        self.norm2 = nn.LayerNorm(hidden_dim, eps=1e-6)
        self.ffn = nn.Sequential(
            nn.Linear(hidden_dim, ffn_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ffn_dim, hidden_dim),
            nn.Dropout(dropout),
        )

    def forward(
        self, x: torch.Tensor, attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        # Pre-LN architecture for training stability
        x = x + self.attn(self.norm1(x), attention_mask=attention_mask)
        x = x + self.ffn(self.norm2(x))
        return x


# ---------------------------------------------------------------------------
# 4. Tathya RoPE Fact Verifier Model Architecture
# ---------------------------------------------------------------------------


class TathyaRoPEVerifier(nn.Module):
    """Deep RoPE-based Fact Verification & Grounding Classifier.

    Classifies Claim-Evidence pairs into 3 verification states:
        0: SUPPORTED
        1: CONTRADICTED
        2: UNSUPPORTED

    Outputs:
        - logits: (batch_size, 3)
        - confidence: (batch_size, 1) probability of top predicted class
        - risk_score: (batch_size, 1) estimated hallucination/tamper risk
    """

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_dim: int = 384,
        num_layers: int = 6,
        num_heads: int = 6,
        ffn_dim: int = 1536,
        max_seq_len: int = 4096,
        num_classes: int = 3,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size

        # Token Embedding (No traditional fixed positional embedding needed because RoPE is used!)
        self.token_embeddings = nn.Embedding(vocab_size, hidden_dim)
        self.embed_dropout = nn.Dropout(dropout)

        # Stack of Transformer blocks with RoPE
        self.layers = nn.ModuleList(
            [
                TransformerBlock(
                    hidden_dim=hidden_dim,
                    num_heads=num_heads,
                    ffn_dim=ffn_dim,
                    dropout=dropout,
                )
                for _ in range(num_layers)
            ]
        )

        self.final_norm = nn.LayerNorm(hidden_dim, eps=1e-6)

        # Classification & Verification Heads
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes),
        )

        self.risk_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 4),
            nn.GELU(),
            nn.Linear(hidden_dim // 4, 1),
            nn.Sigmoid(),
        )

        self._init_weights()

    def _init_weights(self):
        """Initializes weights with Xavier/Normal distributions."""
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        """
        Args:
            input_ids: (batch_size, seq_len) token IDs
            attention_mask: (batch_size, seq_len) attention mask (1 = valid, 0 = pad)

        Returns:
            dict with 'logits', 'probabilities', 'confidence', 'risk_score'
        """
        x = self.token_embeddings(input_ids)
        x = self.embed_dropout(x)

        for layer in self.layers:
            x = layer(x, attention_mask=attention_mask)

        x = self.final_norm(x)

        # Pooled output: Mean pooling over non-padded tokens
        if attention_mask is not None:
            mask_expanded = attention_mask.unsqueeze(-1).expand_as(x)
            sum_embeddings = torch.sum(x * mask_expanded, dim=1)
            sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
            pooled = sum_embeddings / sum_mask
        else:
            pooled = x.mean(dim=1)

        logits = self.classifier(pooled)
        probs = F.softmax(logits, dim=-1)
        confidence, predicted_classes = torch.max(probs, dim=-1)
        risk = self.risk_head(pooled)

        return {
            "logits": logits,
            "probabilities": probs,
            "predictions": predicted_classes,
            "confidence": confidence,
            "risk_score": risk.squeeze(-1),
            "embeddings": pooled,
        }
