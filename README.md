# Medicate AI — Precision Oncology Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vite.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-1E8C1E?style=for-the-badge&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Dhavs786/Genomic-and-Protemic-Precision-medicine)

Medicate AI is a professional, clinical-grade precision medicine platform designed to translate high-throughput pharmacogenomics data into actionable therapeutic decisions. The system integrates basal cell line screening data across both **GDSC1** and **GDSC2** datasets to predict optimal drug sensitivity profile recommendations using an advanced XGBoost machine learning pipeline.

> [!TIP]
> **Detailed Documentation Available:** For a comprehensive guide covering system architecture diagrams, database schema diagrams, REST API endpoints, and step-by-step model training walkthroughs, please check the [Project Guide (PROJECT_GUIDE.md)](file:///d:/DE_project/PROJECT_GUIDE.md).

---

## Key Features

- **Dual-Dataset Harmonzation**: Concurrently trains on **470,000+ screening samples** across GDSC1 and GDSC2, automatically cleaning and merging cell-line attributes from `Cell_Lines_Details.xlsx`.
- **XGBoost Inference Engine**: Achieves **66.7% accuracy and 0.707 test ROC-AUC** for patient-specific therapeutic classification.
- **Vite + React SPA**: A modern clinical dashboard featuring:
  - Interactive Radar & Bar chart efficacy visualizations.
  - Drag-and-drop molecular JSON profile uploading.
  - Real-time observational cohort telemetry.
  - Filterable patient enrollment and tracking registry.
- **FastAPI Backend**: Production-ready, asynchronous API server backed by SQLAlchemy SQLite databases (configured with cascade updates, index optimization, and timezone-aware auditing).

---

## Project layout

```text
DE_project/
├── gdsc_drug_response/   # FastAPI Backend & Core Python Package
│   ├── api.py            # API routing, validation & model serving
│   ├── benchmarks.py     # Joint GDSC1 + GDSC2 release training
│   ├── cli.py            # CLI parser & script runners
│   ├── core.py           # Config dataclasses & helper utilities
│   ├── data.py           # Data ingestion, scaling, & standardization
│   ├── database.py       # SQLAlchemy ORM models, session & engine
│   ├── interpreters.py   # SHAP-based feature importance explainers
│   ├── metrics.py        # Model evaluation & cell-line-aware splitting
│   ├── models.py         # Baseline classification & training pipelines
│   └── seed_data.py      # Automated database demo seeder
├── frontend/             # Vite + React SPA Frontend client
│   ├── src/
│   │   ├── App.jsx       # Single Page Application and UI views
│   │   ├── main.jsx      # React entry point
│   │   └── index.css     # Medicate AI design system stylesheet
│   ├── package.json      # Node.js dependencies (lucide, chartjs, confetti)
│   └── vite.config.js    # Dev proxy configuration to Backend (port 8000)
├── dataset/              # GDSC Raw Tables (GDSC1, GDSC2, Cell Line Details, Compounds)
├── artifacts/            # Model weight checkpoints (release_baseline.joblib)
├── tests/                # Automated pytest unit & integration test suite
├── demo_molecular_profile.json
├── pyproject.toml        # Poetry/pip python project configuration
└── README.md             # Project documentation overview
```

---

## Getting Started

### 1. Installation

Install backend Python dependencies in editable mode:
```bash
pip install -e .
```

Install frontend Node.js packages:
```bash
cd frontend
npm install
cd ..
```

---

## Data Preparation & Model Training

To retrain the unified GDSC1 + GDSC2 baseline model:
```bash
python -m gdsc_drug_response.cli train-release-baseline \
  --release dataset/GDSC_DATASET.csv \
  --release2 dataset/GDSC2-dataset.csv \
  --cell-lines dataset/Cell_Lines_Details.xlsx \
  --compounds dataset/Compounds-annotation.csv \
  --output-dir artifacts/release_baseline
```
This generates the model weights artifact `artifacts/release_baseline/release_baseline.joblib` and evaluates metrics.

---

## Deployment Guide

For local or production deployments, follow these steps to compile the frontend assets and serve them directly via FastAPI:

### 1. Build the React Client
Compile the React source files into optimized production HTML/CSS/JS assets:
```bash
cd frontend
npm run build
cd ..
```
This outputs the compiled static assets into `frontend/dist`. The FastAPI backend is configured to automatically serve these compiled files if the directory is present.

### 2. Seed the Database
Initialize the database schemas and populate demo patients and predictions generated by the new model:
```bash
python -m gdsc_drug_response.seed_data
```
This creates the SQLite database file `hospital.db`.

### 3. Launch the Application Server
Run the FastAPI production application server:
```bash
python -m uvicorn gdsc_drug_response.api:app --host 0.0.0.0 --port 8000
```
Open your browser and navigate to `http://localhost:8000` to access the live Medicate AI application.

---

## Running Tests

Verify backend endpoints, patient registries, uploads, and dashboard telemetry calculations using `pytest`:
```bash
python -m pytest tests/ -v
```
All tests run on in-memory database pools to prevent file pollution.
