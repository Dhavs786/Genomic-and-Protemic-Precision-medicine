from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from gdsc_drug_response.core import DataConfig, ReleaseTableConfig, ensure_directory, read_table


@dataclass(slots=True)
class PreparedDataset:
    expression: pd.DataFrame
    response: pd.DataFrame
    merged: pd.DataFrame


@dataclass(slots=True)
class FeatureSpec:
    gene_columns: list[str]
    categorical_columns: list[str]
    passthrough_columns: list[str]


def standardize_identifier(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", "_", regex=True)
    )


def load_expression_matrix(path: str) -> pd.DataFrame:
    expression = read_table(path)
    first_column = expression.columns[0]
    expression = expression.rename(columns={first_column: "GENE"})
    expression["GENE"] = expression["GENE"].astype(str).str.strip()
    expression = expression.drop_duplicates(subset=["GENE"]).set_index("GENE")
    expression.columns = standardize_identifier(pd.Series(expression.columns)).tolist()
    # Convert from genes x cell-lines to cell-lines x genes.
    expression_t = expression.transpose().reset_index().rename(columns={"index": "CELL_LINE_NAME"})
    expression_t["CELL_LINE_NAME"] = standardize_identifier(expression_t["CELL_LINE_NAME"])
    return expression_t


def select_top_variable_genes(expression_df: pd.DataFrame, n_genes: int | None) -> pd.DataFrame:
    if n_genes is None:
        return expression_df
    gene_columns = [col for col in expression_df.columns if col != "CELL_LINE_NAME"]
    if len(gene_columns) <= n_genes:
        return expression_df
    variances = expression_df[gene_columns].var(axis=0).sort_values(ascending=False)
    selected = variances.head(n_genes).index.tolist()
    return expression_df[["CELL_LINE_NAME", *selected]]


def load_response_table(config: DataConfig) -> pd.DataFrame:
    response = read_table(config.response_path)
    required = [config.cell_line_column, config.drug_column, config.ic50_column]
    missing = [col for col in required if col not in response.columns]
    if missing:
        raise ValueError(f"Response file is missing required columns: {missing}")

    response = response[required].copy()
    response.columns = ["CELL_LINE_NAME", "DRUG_NAME", "IC50"]
    response["CELL_LINE_NAME"] = standardize_identifier(response["CELL_LINE_NAME"])
    response["DRUG_NAME"] = response["DRUG_NAME"].astype(str).str.strip()
    response["IC50"] = pd.to_numeric(response["IC50"], errors="coerce")
    response = response.dropna(subset=["CELL_LINE_NAME", "DRUG_NAME", "IC50"])
    response = response.drop_duplicates(subset=["CELL_LINE_NAME", "DRUG_NAME"], keep="first")
    return response


def load_release_table(config: ReleaseTableConfig) -> pd.DataFrame:
    release = read_table(config.release_path)
    required = [config.cell_line_column, config.drug_column, config.ic50_column]
    missing = [col for col in required if col not in release.columns]
    if missing:
        raise ValueError(f"Release file is missing required columns: {missing}")

    release = release.copy()
    release["CELL_LINE_NAME"] = standardize_identifier(release[config.cell_line_column])
    release["DRUG_NAME"] = release[config.drug_column].astype(str).str.strip()
    release["IC50"] = pd.to_numeric(release[config.ic50_column], errors="coerce")
    release = release.dropna(subset=["CELL_LINE_NAME", "DRUG_NAME", "IC50"])
    release = release.drop_duplicates(subset=["CELL_LINE_NAME", "DRUG_NAME"], keep="first")
    return release


def create_binary_labels(response_df: pd.DataFrame) -> pd.DataFrame:
    thresholds = response_df.groupby("DRUG_NAME")["IC50"].median().rename("IC50_THRESHOLD")
    labeled = response_df.merge(thresholds, on="DRUG_NAME", how="left")
    labeled["LABEL"] = np.where(labeled["IC50"] <= labeled["IC50_THRESHOLD"], 1, 0)
    labeled["RESPONSE_CLASS"] = np.where(labeled["LABEL"] == 1, "Sensitive", "Resistant")
    return labeled


def merge_metadata(merged_df: pd.DataFrame, metadata_path: str | None) -> pd.DataFrame:
    if not metadata_path:
        return merged_df
    metadata = read_table(metadata_path)
    if "CELL_LINE_NAME" not in metadata.columns:
        raise ValueError("Metadata file must contain CELL_LINE_NAME")
    metadata = metadata.copy()
    metadata["CELL_LINE_NAME"] = standardize_identifier(metadata["CELL_LINE_NAME"])
    return merged_df.merge(metadata, on="CELL_LINE_NAME", how="left")


def build_model_dataset(config: DataConfig) -> PreparedDataset:
    expression = load_expression_matrix(str(config.expression_path))
    expression = select_top_variable_genes(expression, config.top_variable_genes)
    response = create_binary_labels(load_response_table(config))
    merged = response.merge(expression, on="CELL_LINE_NAME", how="inner")
    merged = merge_metadata(merged, str(config.metadata_path) if config.metadata_path else None)
    return PreparedDataset(expression=expression, response=response, merged=merged)


def build_release_response_dataset(config: ReleaseTableConfig) -> pd.DataFrame:
    release = load_release_table(config)
    labeled = create_binary_labels(release)

    release_source = read_table(config.release_path).copy()
    release_source["CELL_LINE_NAME"] = standardize_identifier(release_source[config.cell_line_column])
    release_source["DRUG_NAME"] = release_source[config.drug_column].astype(str).str.strip()
    enriched = labeled.merge(
        release_source.drop(columns=[config.ic50_column], errors="ignore"),
        on=["CELL_LINE_NAME", "DRUG_NAME"],
        how="left",
    )

    if config.compounds_path:
        compounds = read_table(config.compounds_path).copy()
        if "DRUG_NAME" in compounds.columns:
            compounds["DRUG_NAME"] = compounds["DRUG_NAME"].astype(str).str.strip()
            enriched = enriched.merge(compounds, on="DRUG_NAME", how="left", suffixes=("", "_compound"))

    return enriched


def save_prepared_dataset(dataset: PreparedDataset, output_dir: str) -> None:
    out_dir = ensure_directory(output_dir)
    dataset.expression.to_csv(out_dir / "expression_prepared.csv", index=False)
    dataset.response.to_csv(out_dir / "response_labeled.csv", index=False)
    dataset.merged.to_csv(out_dir / "model_dataset.csv", index=False)


def save_release_dataset(dataset: pd.DataFrame, output_dir: str) -> None:
    out_dir = ensure_directory(output_dir)
    dataset.to_csv(out_dir / "gdsc_release_labeled.csv", index=False)


def infer_feature_spec(dataset: pd.DataFrame) -> FeatureSpec:
    excluded = {
        "CELL_LINE_NAME",
        "IC50",
        "IC50_THRESHOLD",
        "LABEL",
        "RESPONSE_CLASS",
    }
    categorical_columns = ["DRUG_NAME"]
    passthrough_columns = [
        col for col in dataset.columns
        if col not in excluded and col not in categorical_columns and dataset[col].dtype == "object"
    ]
    gene_columns = [
        col for col in dataset.columns
        if col not in excluded and col not in categorical_columns and col not in passthrough_columns
    ]
    return FeatureSpec(
        gene_columns=gene_columns,
        categorical_columns=categorical_columns,
        passthrough_columns=passthrough_columns,
    )
