from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass(slots=True)
class DataConfig:
    expression_path: Path
    response_path: Path
    metadata_path: Path | None = None
    output_dir: Path = Path("data/processed")
    cell_line_column: str = "CELL_LINE_NAME"
    drug_column: str = "DRUG_NAME"
    ic50_column: str = "IC50"
    top_variable_genes: int | None = 2000


@dataclass(slots=True)
class ReleaseTableConfig:
    release_path: Path
    compounds_path: Path | None = None
    output_dir: Path = Path("data/processed")
    cell_line_column: str = "CELL_LINE_NAME"
    drug_column: str = "DRUG_NAME"
    ic50_column: str = "LN_IC50"


@dataclass(slots=True)
class TrainConfig:
    dataset_path: Path
    output_dir: Path = Path("artifacts")
    model_type: str = "xgboost"
    test_size: float = 0.15
    val_size: float = 0.15
    random_state: int = 42
    positive_label: str = "Sensitive"
    negative_label: str = "Resistant"
    metadata_columns: list[str] = field(default_factory=list)


def infer_sep(path: Path) -> str:
    if path.suffix.lower() in {".tsv", ".txt"}:
        return "\t"
    return ","


def read_table(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    return pd.read_csv(file_path, sep=infer_sep(file_path))


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
