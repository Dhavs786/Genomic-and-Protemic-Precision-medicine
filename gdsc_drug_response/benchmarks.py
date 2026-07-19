from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from gdsc_drug_response.core import ensure_directory, read_table
from gdsc_drug_response.data import infer_feature_spec, standardize_identifier
from gdsc_drug_response.metrics import classification_metrics, split_by_cell_line
from gdsc_drug_response.models import build_training_pipeline


def prepare_release_frame(
    release_path: str | Path,
    release2_path: str | Path | None = None,
    cell_lines_path: str | Path | None = None,
    compounds_path: str | Path | None = None,
) -> pd.DataFrame:
    release = read_table(release_path)
    release["CELL_LINE_NAME"] = standardize_identifier(release["CELL_LINE_NAME"])
    release["DRUG_NAME"] = release["DRUG_NAME"].astype(str).str.strip()
    release["LN_IC50"] = pd.to_numeric(release["LN_IC50"], errors="coerce")
    release = release.dropna(subset=["CELL_LINE_NAME", "DRUG_NAME", "LN_IC50"]).copy()
    release = release.drop_duplicates(subset=["CELL_LINE_NAME", "DRUG_NAME"], keep="first")

    if release2_path:
        if not cell_lines_path:
            raise ValueError("cell_lines_path must be provided if release2_path is specified.")
        
        release2 = read_table(release2_path)
        # Rename columns to ensure consistency
        if "COSMIC_ID" not in release2.columns and "COSMIC identifier" in release2.columns:
            release2 = release2.rename(columns={"COSMIC identifier": "COSMIC_ID"})
        
        release2["CELL_LINE_NAME"] = standardize_identifier(release2["CELL_LINE_NAME"])
        release2["DRUG_NAME"] = release2["DRUG_NAME"].astype(str).str.strip()
        release2["LN_IC50"] = pd.to_numeric(release2["LN_IC50"], errors="coerce")
        release2 = release2.dropna(subset=["CELL_LINE_NAME", "DRUG_NAME", "LN_IC50"]).copy()
        release2 = release2.drop_duplicates(subset=["CELL_LINE_NAME", "DRUG_NAME"], keep="first")

        # Load cell line metadata sheet
        meta = pd.read_excel(cell_lines_path, sheet_name="Cell line details")
        meta.columns = [" ".join(c.split()) for c in meta.columns]
        meta = meta.rename(columns={
            "COSMIC identifier": "COSMIC_ID",
            "Sample Name": "CELL_LINE_NAME",
            "Copy Number Alterations (CNA)": "CNA",
        })

        meta_cols = [
            "COSMIC_ID", "GDSC Tissue descriptor 1", "GDSC Tissue descriptor 2",
            "Cancer Type (matching TCGA label)", "Microsatellite instability Status (MSI)",
            "Screen Medium", "Growth Properties", "CNA", "Gene Expression", "Methylation"
        ]
        # Only keep columns that are present in the Excel sheet
        meta_cols = [c for c in meta_cols if c in meta.columns]
        meta = meta[meta_cols].copy()

        # Merge metadata onto GDSC2
        release2 = release2.merge(meta, on="COSMIC_ID", how="left")

        # Add dataset indicator
        release["DATASET"] = "GDSC1"
        release2["DATASET"] = "GDSC2"

        # Align columns and concatenate
        common_cols = [c for c in release.columns if c in release2.columns]
        release = pd.concat([release[common_cols], release2[common_cols]], ignore_index=True)

    thresholds = release.groupby("DRUG_NAME")["LN_IC50"].median().rename("IC50_THRESHOLD")
    release = release.merge(thresholds, on="DRUG_NAME", how="left")
    release["LABEL"] = (release["LN_IC50"] <= release["IC50_THRESHOLD"]).astype(int)
    release["RESPONSE_CLASS"] = release["LABEL"].map({1: "Sensitive", 0: "Resistant"})

    if compounds_path:
        compounds = read_table(compounds_path)
        compounds["DRUG_NAME"] = compounds["DRUG_NAME"].astype(str).str.strip()
        compounds = compounds.sort_values(["DRUG_NAME"]).drop_duplicates(subset=["DRUG_NAME"], keep="first")
        release = release.merge(compounds, on="DRUG_NAME", how="left", suffixes=("", "_compound"))
        # Drop duplicate columns introduced by the merge
        compound_dupes = [c for c in release.columns if c.endswith("_compound")]
        release = release.drop(columns=compound_dupes)

    return release


def train_release_baseline(
    release_path: str | Path,
    output_dir: str | Path,
    release2_path: str | Path | None = None,
    cell_lines_path: str | Path | None = None,
    compounds_path: str | Path | None = None,
    random_state: int = 42,
) -> dict[str, object]:
    """
    Retrains the baseline model using the superior XGBoost technique.
    """
    dataset = prepare_release_frame(release_path, release2_path, cell_lines_path, compounds_path)
    
    # Define features for the release table
    feature_columns_pool = [
        "DRUG_NAME", "TCGA_DESC", "TARGET", "TARGET_PATHWAY",
        "GDSC Tissue descriptor 1", "GDSC Tissue descriptor 2",
        "Cancer Type (matching TCGA label)", "Microsatellite instability Status (MSI)",
        "Screen Medium", "Growth Properties", "Gene Expression",
        "CNA", "Methylation", "PUTATIVE_TARGET", "PATHWAY_NAME",
    ]
    feature_columns = [column for column in feature_columns_pool if column in dataset.columns]

    split = split_by_cell_line(dataset, random_state=random_state)
    
    # Use the advanced XGBoost pipeline from models.py
    feature_spec = infer_feature_spec(split.train[feature_columns + ["LABEL"]])
    # Force categorical for release table features
    feature_spec.categorical_columns = feature_columns
    feature_spec.gene_columns = []
    feature_spec.passthrough_columns = []
    
    pipeline = build_training_pipeline(feature_spec, model_type="xgboost")
    pipeline.fit(split.train[feature_columns], split.train["LABEL"])

    val_scores = pipeline.predict_proba(split.validation[feature_columns])[:, 1]
    test_scores = pipeline.predict_proba(split.test[feature_columns])[:, 1]
    val_pred = (val_scores >= 0.5).astype(int)
    test_pred = (test_scores >= 0.5).astype(int)

    val_metrics = classification_metrics(split.validation["LABEL"], val_pred, val_scores)
    test_metrics = classification_metrics(split.test["LABEL"], test_pred, test_scores)

    drug_metrics = []
    for drug_name, group in split.test.assign(pred=test_pred, score=test_scores).groupby("DRUG_NAME"):
        metrics = classification_metrics(group["LABEL"], group["pred"], group["score"])
        drug_metrics.append({"DRUG_NAME": drug_name, **metrics})
    drug_metrics_df = pd.DataFrame(drug_metrics).sort_values("roc_auc", ascending=False, na_position="last")

    out_dir = ensure_directory(output_dir)
    dataset.to_csv(out_dir / "gdsc_release_labeled.csv", index=False)
    pd.DataFrame([val_metrics]).to_csv(out_dir / "validation_metrics.csv", index=False)
    pd.DataFrame([test_metrics]).to_csv(out_dir / "test_metrics.csv", index=False)
    drug_metrics_df.to_csv(out_dir / "per_drug_metrics.csv", index=False)
    
    # Save as joblib for consistency with api.py
    joblib.dump({
        "pipeline": pipeline,
        "feature_spec": feature_spec,
        "feature_columns": feature_columns
    }, out_dir / "release_baseline.joblib")
    
    with (out_dir / "training_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "model_type": "xgboost_baseline",
                "n_rows": int(len(dataset)),
                "n_train": int(len(split.train)),
                "n_validation": int(len(split.validation)),
                "n_test": int(len(split.test)),
                "n_drugs": int(dataset["DRUG_NAME"].nunique()),
                "feature_columns": feature_columns,
                "validation_metrics": val_metrics,
                "test_metrics": test_metrics,
            },
            fh,
            indent=2,
        )

    return {
        "output_dir": str(out_dir),
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
    }
