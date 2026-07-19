from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit


@dataclass(slots=True)
class DatasetSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def split_by_cell_line(
    dataset: pd.DataFrame,
    group_column: str = "CELL_LINE_NAME",
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = 42,
) -> DatasetSplit:
    groups = dataset[group_column]
    first_split = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_val_idx, test_idx = next(first_split.split(dataset, groups=groups))
    train_val = dataset.iloc[train_val_idx].reset_index(drop=True)
    test = dataset.iloc[test_idx].reset_index(drop=True)

    relative_val_size = val_size / (1.0 - test_size)
    second_split = GroupShuffleSplit(n_splits=1, test_size=relative_val_size, random_state=random_state)
    train_idx, val_idx = next(second_split.split(train_val, groups=train_val[group_column]))
    train = train_val.iloc[train_idx].reset_index(drop=True)
    validation = train_val.iloc[val_idx].reset_index(drop=True)
    return DatasetSplit(train=train, validation=validation, test=test)


def classification_metrics(y_true: pd.Series, y_pred: np.ndarray, y_score: np.ndarray) -> dict[str, float]:
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = roc_auc_score(y_true, y_score)
    else:
        metrics["roc_auc"] = float("nan")
    return metrics


def per_drug_metrics(y_true: pd.Series, y_pred: np.ndarray, y_score: np.ndarray, drug_names: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "y_true": y_true,
            "y_pred": y_pred,
            "y_score": y_score,
            "DRUG_NAME": drug_names,
        }
    )
    rows = []
    for drug_name, group in frame.groupby("DRUG_NAME"):
        rows.append({"DRUG_NAME": drug_name, **classification_metrics(group["y_true"], group["y_pred"], group["y_score"])})
    return pd.DataFrame(rows).sort_values("roc_auc", ascending=False, na_position="last")
