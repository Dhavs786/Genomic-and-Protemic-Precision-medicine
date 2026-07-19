from __future__ import annotations

import argparse

from gdsc_drug_response.core import DataConfig, ReleaseTableConfig, TrainConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GDSC drug response pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preprocess_parser = subparsers.add_parser("preprocess", help="Build merged model dataset")
    preprocess_parser.add_argument("--expression", required=True)
    preprocess_parser.add_argument("--response", required=True)
    preprocess_parser.add_argument("--metadata")
    preprocess_parser.add_argument("--output-dir", default="data/processed")
    preprocess_parser.add_argument("--top-variable-genes", type=int, default=2000)

    release_parser = subparsers.add_parser(
        "preprocess-release",
        help="Clean a row-wise GDSC release table and create per-drug labels",
    )
    release_parser.add_argument("--release", required=True)
    release_parser.add_argument("--compounds")
    release_parser.add_argument("--output-dir", default="data/processed")
    release_parser.add_argument("--ic50-column", default="LN_IC50")

    train_parser = subparsers.add_parser("train", help="Train baseline classifier")
    train_parser.add_argument("--dataset", required=True)
    train_parser.add_argument("--output-dir", default="artifacts")
    train_parser.add_argument(
        "--model-type",
        default="xgboost",
        choices=["xgboost", "logistic_regression", "random_forest"],
    )
    train_parser.add_argument("--test-size", type=float, default=0.15)
    train_parser.add_argument("--val-size", type=float, default=0.15)
    train_parser.add_argument("--random-state", type=int, default=42)

    release_train_parser = subparsers.add_parser(
        "train-release-baseline",
        help="Train a no-download baseline model on the uploaded row-wise GDSC release table",
    )
    release_train_parser.add_argument("--release", required=True)
    release_train_parser.add_argument("--release2", default=None, help="Optional second release table (e.g. GDSC2)")
    release_train_parser.add_argument("--cell-lines", default=None, help="Optional Excel file containing cell line details")
    release_train_parser.add_argument("--compounds")
    release_train_parser.add_argument("--output-dir", default="artifacts/release_baseline")
    release_train_parser.add_argument("--random-state", type=int, default=42)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "preprocess":
        from gdsc_drug_response.data import build_model_dataset, save_prepared_dataset

        config = DataConfig(
            expression_path=args.expression,
            response_path=args.response,
            metadata_path=args.metadata,
            output_dir=args.output_dir,
            top_variable_genes=args.top_variable_genes,
        )
        dataset = build_model_dataset(config)
        save_prepared_dataset(dataset, args.output_dir)
        return

    if args.command == "preprocess-release":
        from gdsc_drug_response.data import build_release_response_dataset, save_release_dataset

        config = ReleaseTableConfig(
            release_path=args.release,
            compounds_path=args.compounds,
            output_dir=args.output_dir,
            ic50_column=args.ic50_column,
        )
        dataset = build_release_response_dataset(config)
        save_release_dataset(dataset, args.output_dir)
        return

    if args.command == "train":
        from gdsc_drug_response.models import train_baseline_model

        config = TrainConfig(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            model_type=args.model_type,
            test_size=args.test_size,
            val_size=args.val_size,
            random_state=args.random_state,
        )
        train_baseline_model(config)
        return

    if args.command == "train-release-baseline":
        from gdsc_drug_response.benchmarks import train_release_baseline

        train_release_baseline(
            release_path=args.release,
            release2_path=args.release2,
            cell_lines_path=args.cell_lines,
            compounds_path=args.compounds,
            output_dir=args.output_dir,
            random_state=args.random_state,
        )


if __name__ == "__main__":
    main()
