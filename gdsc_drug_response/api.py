from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gdsc_drug_response.database import (
    Patient,
    Prediction as DBPrediction,
    Report as DBReport,
    get_db,
    init_db as initialize_database,
)

# --- Constants ---

DRUG_PANEL = [
    "Cisplatin", "Docetaxel", "Gemcitabine",
    "Paclitaxel", "Vinblastine", "Erlotinib", "Gefitinib",
]


class Predictor:
    def __init__(self, artifact_path: str | Path):
        self.path = Path(artifact_path)
        artifact = joblib.load(self.path)
        self.model = artifact["pipeline"]
        self.feature_columns = artifact["feature_columns"]
        self.feature_spec = artifact.get("feature_spec")

    def predict_ranked_drugs(self, features: dict[str, Any], drugs: list[str]) -> pd.DataFrame:
        rows = []
        for drug in drugs:
            row = {"DRUG_NAME": drug}
            row.update(features)
            rows.append(row)
        
        import numpy as np
        frame = pd.DataFrame(rows)
        for column in self.feature_columns:
            if column not in frame.columns:
                frame[column] = np.nan
        
        frame = frame[self.feature_columns]
        
        probabilities = self.model.predict_proba(frame)[:, 1]

        result = pd.DataFrame({
            "DRUG_NAME": drugs,
            "probability_sensitive": probabilities,
        }).sort_values("probability_sensitive", ascending=False)
        
        result["predicted_label"] = result["probability_sensitive"].ge(0.5).map({True: "Sensitive", False: "Resistant"})
        return result.reset_index(drop=True)


# --- Pydantic Models ---

class PatientCreate(BaseModel):
    name: str
    email: str


class PredictionRow(BaseModel):
    drug_name: str
    probability_sensitive: float
    predicted_label: str


class UploadResponse(BaseModel):
    report_id: int
    predictions: list[PredictionRow]


# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    initialize_database()
    yield

app = FastAPI(title="Precision Medicine API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_predictor() -> Predictor:
    paths = [
        os.getenv("GDSC_MODEL_PATH", "artifacts/model.joblib"),
        "artifacts/release_baseline/release_baseline.joblib",
    ]
    for p in paths:
        if os.path.exists(p):
            return Predictor(p)
    raise HTTPException(status_code=500, detail="No model artifact found. Train a model first.")


# --- API Endpoints ---

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/patients", response_model=dict[str, Any])
def register_patient(patient_in: PatientCreate, db: Session = Depends(get_db)):
    db_patient = db.query(Patient).filter(Patient.email == patient_in.email).first()
    if db_patient:
        return {"id": db_patient.id, "name": db_patient.name, "email": db_patient.email, "status": "existing"}
    
    new_patient = Patient(name=patient_in.name, email=patient_in.email)
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return {"id": new_patient.id, "name": new_patient.name, "email": new_patient.email, "status": "created"}


@app.post("/patients/{patient_id}/upload", response_model=UploadResponse)
def upload_data(patient_id: int, features: dict[str, Any], db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    predictor = get_predictor()
    ranked = predictor.predict_ranked_drugs(features, DRUG_PANEL)
    
    # Save Report
    report = DBReport(patient_id=patient_id, filename="molecular_profile.json")
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Save Predictions
    predictions = []
    for _, row in ranked.iterrows():
        db_pred = DBPrediction(
            report_id=report.id,
            drug_name=row["DRUG_NAME"],
            score=float(row["probability_sensitive"]),
            label=row["predicted_label"]
        )
        db.add(db_pred)
        predictions.append({
            "drug_name": row["DRUG_NAME"],
            "probability_sensitive": float(row["probability_sensitive"]),
            "predicted_label": row["predicted_label"]
        })
    
    db.commit()
    return {"report_id": report.id, "predictions": predictions}


@app.get("/doctor/dashboard")
def get_doctor_dashboard(db: Session = Depends(get_db)):
    patients = db.query(Patient).all()
    results = []
    
    total_sensitive_count = 0
    total_predictions = 0
    drug_sensitivity_counts: dict[str, int] = {}
    all_scores: list[float] = []

    for p in patients:
        latest_report = (
            db.query(DBReport)
            .filter(DBReport.patient_id == p.id)
            .order_by(DBReport.uploaded_at.desc())
            .first()
        )
        top_drugs = []
        if latest_report:
            preds = db.query(DBPrediction).filter(DBPrediction.report_id == latest_report.id).all()
            for pred in preds:
                total_predictions += 1
                all_scores.append(pred.score)
                if pred.label == "Sensitive":
                    total_sensitive_count += 1
                drug_sensitivity_counts[pred.drug_name] = (
                    drug_sensitivity_counts.get(pred.drug_name, 0)
                    + (1 if pred.label == "Sensitive" else 0)
                )

            top_drugs = sorted(preds, key=lambda x: x.score, reverse=True)[:3]
            top_drugs = [{"drug": d.drug_name, "score": d.score} for d in top_drugs]
        
        results.append({
            "patient_id": p.id,
            "name": p.name,
            "email": p.email,
            "latest_report_date": latest_report.uploaded_at if latest_report else None,
            "top_recommendations": top_drugs
        })

    model_confidence = sum(all_scores) / len(all_scores) if all_scores else None

    # Global Statistics
    stats = {
        "total_patients": len(patients),
        "population_sensitivity": (total_sensitive_count / total_predictions * 100) if total_predictions > 0 else 0,
        "most_sensitive_drug": max(drug_sensitivity_counts, key=drug_sensitivity_counts.get) if drug_sensitivity_counts else "N/A",
        "model_confidence": model_confidence,
    }

    return {"patients": results, "stats": stats}


# Mount static files for frontend
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
elif os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
