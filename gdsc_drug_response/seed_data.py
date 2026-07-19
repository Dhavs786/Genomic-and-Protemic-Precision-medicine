from __future__ import annotations

from sqlalchemy.orm import Session

from gdsc_drug_response.database import SessionLocal, Patient, Report, Prediction, init_db
from gdsc_drug_response.api import get_predictor

def seed():
    print("Seeding database with demo data...")
    init_db()
    db: Session = SessionLocal()
    
    # Check if we already have data
    if db.query(Patient).count() > 0:
        print("Database already seeded. Skipping.")
        db.close()
        return

    # Demo Patients
    demo_patients = [
        {"name": "Michael Chen", "email": "m.chen@example.com", "tissue": "lung", "tcga": "LUAD"},
        {"name": "Sarah Johnson", "email": "s.johnson@medical.io", "tissue": "breast", "tcga": "BRCA"},
        {"name": "David Miller", "email": "d.miller@gmail.com", "tissue": "skin", "tcga": "SKCM"},
    ]

    predictor = get_predictor()
    sample_drugs = ["Cisplatin", "Docetaxel", "Gemcitabine", "Paclitaxel", "Vinblastine", "Erlotinib", "Gefitinib", "Bortezomib", "Doxorubicin", "5-Fluorouracil"]

    for p_data in demo_patients:
        patient = Patient(name=p_data["name"], email=p_data["email"])
        db.add(patient)
        db.commit()
        db.refresh(patient)

        # Create a report for this patient
        report = Report(patient_id=patient.id, filename="initial_molecular_profile.json")
        db.add(report)
        db.commit()
        db.refresh(report)

        # Mock features based on their cancer type
        features = {
            "TCGA_DESC": p_data["tcga"],
            "GDSC Tissue descriptor 1": p_data["tissue"],
            "Cancer Type (matching TCGA label)": p_data["tcga"],
            "Screen Medium": "RPMI",
            "Gene Expression": "Y",
            "CNA": "Y",
            "Methylation": "Y"
        }

        # Predict
        ranked = predictor.predict_ranked_drugs(features, sample_drugs)
        
        for _, row in ranked.iterrows():
            pred = Prediction(
                report_id=report.id,
                drug_name=row["DRUG_NAME"],
                score=float(row["probability_sensitive"]),
                label=row["predicted_label"]
            )
            db.add(pred)
        
        print(f"Added patient: {patient.name} with {len(ranked)} predictions.")

    db.commit()
    db.close()
    print("Database seeding complete!")

if __name__ == "__main__":
    seed()
