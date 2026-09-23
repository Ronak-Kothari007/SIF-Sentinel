"""
SIF Sentinel -- Phase 5: DistilBERT SIF Precursor Classifier
=============================================================

Dataset for Fine-Tuning:
    Small dataset (34 train / 8 val / 8 test). Strategy:
    - Use pretrained distilbert-base-uncased.
    - Fine-tune ALL layers with a very low LR (2e-5) to avoid catastrophic
      forgetting on such a small dataset.
    - Apply class-weighted loss to handle imbalance.
    - Early stopping on val F2 with patience=3.
    - Max 10 epochs to prevent overfitting.

    DistilBERT is ~40% smaller and ~60% faster than BERT while retaining
    97% of BERT's performance, making it ideal for local prototype inference.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

# Safe encoding for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 256       # token limit; most safety reports < 100 tokens
DEFAULT_THRESHOLD = 0.50  # classification threshold (configurable)


# ---------------------------------------------------------------------------
# PyTorch Dataset
# ---------------------------------------------------------------------------

class SIFDataset(Dataset):
    """
    Wraps report_text + sif_precursor labels for DistilBERT fine-tuning.

    The tokenizer is applied at construction time so that DataLoader workers
    do not need to serialise the tokenizer across processes.
    """

    def __init__(
        self,
        texts: list[str],
        labels: list[int],
        tokenizer,
        max_length: int = MAX_LENGTH,
    ):
        from transformers import PreTrainedTokenizerBase
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict:
        item = {key: val[idx] for key, val in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item


# ---------------------------------------------------------------------------
# CSV loading helper
# ---------------------------------------------------------------------------

def load_split(path: Path) -> tuple[list[str], list[int]]:
    """Load a split CSV into (texts, labels)."""
    df = pd.read_csv(path, dtype={"sif_precursor": int, "report_id": str})
    missing = {"report_text", "sif_precursor"} - set(df.columns)
    if missing:
        raise ValueError(f"CSV at {path} is missing columns: {missing}")
    return df["report_text"].astype(str).tolist(), df["sif_precursor"].tolist()


# ---------------------------------------------------------------------------
# Class-weight helper
# ---------------------------------------------------------------------------

def compute_class_weights(labels: list[int]) -> torch.Tensor:
    """
    Compute inverse-frequency class weights for binary classification.

    Weight for class c = total_samples / (n_classes * count_c).
    This is sklearn's 'balanced' strategy, implemented in pure Python/PyTorch.
    """
    counts = {0: labels.count(0), 1: labels.count(1)}
    n = len(labels)
    n_classes = 2
    weights = torch.tensor(
        [n / (n_classes * counts[c]) for c in [0, 1]],
        dtype=torch.float,
    )
    return weights
