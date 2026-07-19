from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import shap
except ImportError:  # pragma: no cover
    shap = None


def generate_shap_summary(pipeline, sample_frame: pd.DataFrame, output_path: str | Path, max_samples: int = 200) -> Path | None:
    if shap is None:
        return None

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    sample = sample_frame.head(max_samples)
    transformed = pipeline.named_steps["preprocessor"].transform(sample)
    classifier = pipeline.named_steps["classifier"]

    explainer = shap.Explainer(classifier)
    shap_values = explainer(transformed)
    values = getattr(shap_values, "values", shap_values)

    mean_importance = pd.DataFrame(
        {
            "feature_index": range(values.shape[1]),
            "mean_abs_shap": abs(values).mean(axis=0),
        }
    ).sort_values("mean_abs_shap", ascending=False)
    mean_importance.to_csv(output_file, index=False)
    return output_file
