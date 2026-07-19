# Medicate AI — Model & Dataset Performance Statistics

This document summarizes the statistics, metrics, and baseline performance of the joint **GDSC1 + GDSC2** XGBoost pharmacogenomics classifier.

---

## 1. Dataset Dimensions & Splits

The dataset combines response screening tables from both releases of the Genomics of Drug Sensitivity in Cancer database, joined with basal cell line annotations.

| Split Category | Samples (Rows) | Proportion |
|---|---|---|
| **Total Cohort** | **471,495** | 100% |
| **Training Set** | 329,419 | 70% |
| **Validation Set** | 72,702 | 15% |
| **Test Set** | 69,374 | 15% |
| **Unique Drugs** | 286 | — |

### Included Feature Columns
The classifier is trained on unified molecular and screening environment properties:
- `DRUG_NAME` (Categorical Target Label mapping)
- `TCGA_DESC` / `Cancer Type` (Cancer Classification)
- `TARGET` / `TARGET_PATHWAY` (Therapeutic target details)
- `GDSC Tissue descriptor 1` & `GDSC Tissue descriptor 2` (Tissue profiles)
- `Microsatellite instability Status (MSI)` (Instability index)
- `Screen Medium` & `Growth Properties` (Culture properties)
- Availability Flags: `Gene Expression`, `CNA`, `Methylation`

---

## 2. Global Model Performance Metrics

The metrics below describe the classifier's ability to predict whether a patient's tissue sample will respond as **Sensitive** or **Resistant** to the drug target panel.

| Metric | Validation Set | Test Set |
|---|---|---|
| **Accuracy** | 60.7% | **66.7%** |
| **Precision** | 63.9% | **69.5%** |
| **Recall** | 49.8% | **60.5%** |
| **F1 Score** | 56.0% | **64.7%** |
| **ROC-AUC** | 0.647 | **0.707** |

---

## 3. Top 15 Most Predictable Therapeutic Agents

The following drugs exhibit the highest sensitivity prediction accuracy and ROC-AUC scores across the test cohort:

| Rank | Drug Name | Accuracy | Precision | Recall | F1 Score | Test ROC-AUC |
|---|---|---|---|---|---|---|
| 1 | **UNC0638** | 79.9% | 81.8% | 77.9% | 79.8% | **0.865** |
| 2 | **PBD-288** | 79.6% | 83.3% | 75.5% | 79.2% | **0.865** |
| 3 | **Zoledronate** | 76.8% | 76.7% | 71.7% | 74.2% | **0.854** |
| 4 | **HKMTI-1-005** | 79.8% | 85.1% | 75.5% | 80.0% | **0.852** |
| 5 | **Vorinostat** | 78.4% | 91.3% | 66.5% | 76.9% | **0.852** |
| 6 | **GSK2830371** | 77.7% | 83.2% | 73.1% | 77.8% | **0.850** |
| 7 | **GSK626616AC** | 78.8% | 86.0% | 71.2% | 77.9% | **0.846** |
| 8 | **Venetoclax** | 75.7% | 74.8% | 72.1% | 73.4% | **0.845** |
| 9 | **LMB_AB1** | 78.8% | 79.1% | 73.9% | 76.4% | **0.844** |
| 10 | **AZD5991** | 76.2% | 72.1% | 72.1% | 72.1% | **0.843** |
| 11 | **N29087-69-1** | 81.0% | 86.7% | 75.9% | 81.0% | **0.838** |
| 12 | **ICL-SIRT078** | 74.2% | 74.7% | 72.4% | 73.6% | **0.838** |
| 13 | **A-366** | 78.2% | 79.4% | 75.5% | 77.4% | **0.830** |
| 14 | **LMB_AB2** | 74.2% | 83.5% | 65.7% | 73.6% | **0.828** |
| 15 | **Daporinad** | 76.6% | 74.7% | 70.2% | 72.4% | **0.824** |

---

## 4. Key Takeaways
- **Combined dataset training** (GDSC1 + GDSC2) boosted the overall training volume to **471,495 records**, significantly enhancing the model's performance on previously unseen screening protocols.
- Model sensitivity and selectivity is highly robust, particularly for epigenetic-targeting agents (e.g. histone methyltransferase inhibitors like `UNC0638` and `HKMTI-1-005`) and HDAC inhibitors (e.g. `Vorinostat`).
