from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from gdsc_drug_response.core import TrainConfig, ensure_directory, read_table
from gdsc_drug_response.data import FeatureSpec, infer_feature_spec
from gdsc_drug_response.interpreters import generate_shap_summary
from gdsc_drug_response.metrics import classification_metrics, per_drug_metrics, split_by_cell_line

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None


@dataclass(slots=True)
class TrainArtifacts:
    pipeline: Pipeline
    feature_spec: FeatureSpec
    metrics: dict[str, float]


def build_preprocessor(feature_spec: FeatureSpec) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    transformers = []
    if feature_spec.gene_columns:
        transformers.append(("genes", numeric_pipeline, feature_spec.gene_columns))
    if feature_spec.categorical_columns or feature_spec.passthrough_columns:
        transformers.append(
            (
                "categorical",
                categorical_pipeline,
                [*feature_spec.categorical_columns, *feature_spec.passthrough_columns],
            )
        )
    return ColumnTransformer(transformers=transformers)


def build_estimator(model_type: str):
    if model_type == "logistic_regression":
        return LogisticRegression(max_iter=2000, class_weight="balanced")
    if model_type == "random_forest":
        return RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced_subsample",
            n_jobs=-1,
        )
    if model_type == "xgboost":
        if XGBClassifier is None:
            raise ImportError("xgboost is not installed. Install it or choose another model.")
        return XGBClassifier(
            n_estimators=250,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=42,
        )
    raise ValueError(f"Unsupported model_type: {model_type}")


def build_training_pipeline(feature_spec: FeatureSpec, model_type: str) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(feature_spec)),
            ("classifier", build_estimator(model_type)),
        ]
    )


def predict_probabilities(pipeline: Pipeline, frame: pd.DataFrame) -> pd.Series:
    probabilities = pipeline.predict_proba(frame)[:, 1]
    return pd.Series(probabilities, index=frame.index, name="probability_sensitive")


def train_baseline_model(config: TrainConfig) -> dict[str, object]:
    dataset = read_table(config.dataset_path)
    splits = split_by_cell_line(
        dataset=dataset,
        test_size=config.test_size,
        val_size=config.val_size,
        random_state=config.random_state,
    )

    feature_spec = infer_feature_spec(splits.train)
    feature_columns = [*feature_spec.gene_columns, *feature_spec.categorical_columns, *feature_spec.passthrough_columns]
    pipeline = build_training_pipeline(feature_spec, config.model_type)

    pipeline.fit(splits.train[feature_columns], splits.train["LABEL"])

    predictions = pipeline.predict(splits.test[feature_columns])
    probabilities = pipeline.predict_proba(splits.test[feature_columns])[:, 1]
    metrics = classification_metrics(splits.test["LABEL"], predictions, probabilities)
    drug_metrics = per_drug_metrics(splits.test["LABEL"], predictions, probabilities, splits.test["DRUG_NAME"])

    output_dir = ensure_directory(config.output_dir)
    joblib.dump(
        {
            "pipeline": pipeline,
            "feature_spec": feature_spec,
            "feature_columns": feature_columns,
        },
        output_dir / "model.joblib",
    )
    pd.DataFrame([metrics]).to_csv(output_dir / "metrics.csv", index=False)
    drug_metrics.to_csv(output_dir / "per_drug_metrics.csv", index=False)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    generate_shap_summary(pipeline, splits.test[feature_columns], output_dir / "shap_summary.csv")

    return {
        "metrics": metrics,
        "output_dir": Path(output_dir),
    }
