# Uploaded Dataset Summary

## Files detected

- `dataset/GDSC_DATASET.csv`
- `dataset/GDSC2-dataset.csv`
- `dataset/Compounds-annotation.csv`
- `dataset/Cell_Lines_Details.xlsx`

## What these files provide

- `GDSC_DATASET.csv`: drug response plus cell-line and drug metadata.
- `GDSC2-dataset.csv`: drug response table for the GDSC2 screen.
- `Compounds-annotation.csv`: drug target and pathway annotations.
- `Cell_Lines_Details.xlsx`: additional cell-line metadata.

## Important constraint

The uploaded release table does not include the actual basal gene-expression matrix.

The `Gene Expression` column in `GDSC_DATASET.csv` is an availability flag such as `Y` or `N`, not a vector of gene features.

## Current project support

The repository can already:

- Clean and label the uploaded row-wise release tables with `preprocess-release`.
- Merge drug annotations into the labeled response dataset.
- Train the full gene-expression model once the basal expression matrix is added.

## Next required file for the full model

To implement the original plan exactly as intended, add the GDSC basal expression matrix file under `dataset/` or `data/raw/`.

Expected structure:

- rows are genes
- columns are cell lines
- values are normalized expression values
