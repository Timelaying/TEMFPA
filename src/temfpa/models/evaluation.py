"""Model evaluation metrics."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)


def evaluate_classifier(
    y_true,
    y_pred,
    y_proba,
) -> dict:
    """Compute classification metrics.

    Returns:
        accuracy, precision_macro, recall_macro, f1_macro, log_loss, confusion_matrix (3x3 list)
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    y_proba = np.asarray(y_proba)

    labels = [0, 1, 2]

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, average="macro", labels=labels, zero_division=0))
    rec = float(recall_score(y_true, y_pred, average="macro", labels=labels, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0))

    try:
        ll = float(log_loss(y_true, y_proba, labels=labels))
    except Exception:
        ll = float("nan")

    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()

    return {
        "accuracy": acc,
        "precision_macro": prec,
        "recall_macro": rec,
        "f1_macro": f1,
        "log_loss": ll,
        "confusion_matrix": cm,
    }


def evaluate_goals(
    y_true_home,
    y_true_away,
    pred_home,
    pred_away,
) -> dict:
    """Evaluate goal prediction accuracy.

    Returns:
        mae_home, mae_away, mae_total, exact_score_accuracy
    """
    y_true_home = np.asarray(y_true_home, dtype=float)
    y_true_away = np.asarray(y_true_away, dtype=float)
    pred_home = np.asarray(pred_home, dtype=float)
    pred_away = np.asarray(pred_away, dtype=float)

    mae_home = float(np.mean(np.abs(y_true_home - pred_home)))
    mae_away = float(np.mean(np.abs(y_true_away - pred_away)))
    mae_total = (mae_home + mae_away) / 2.0

    # Exact score: round predictions and compare
    exact = float(
        np.mean(
            (np.round(pred_home) == y_true_home)
            & (np.round(pred_away) == y_true_away)
        )
    )

    return {
        "mae_home": mae_home,
        "mae_away": mae_away,
        "mae_total": mae_total,
        "exact_score_accuracy": exact,
    }


def format_report(metrics: dict) -> str:
    """Format a metrics dict into a human-readable text summary."""
    lines = ["=== Model Evaluation Report ==="]
    for key, value in metrics.items():
        if key == "confusion_matrix":
            lines.append("Confusion Matrix:")
            for row in value:
                lines.append("  " + "  ".join(f"{x:4d}" for x in row))
        elif isinstance(value, float):
            lines.append(f"  {key}: {value:.4f}")
        else:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)
