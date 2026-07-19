import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gdsc_drug_response.api import app
from gdsc_drug_response.database import Base, get_db

# In-memory SQLite database for tests — no leftover files
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_new_patient():
    response = client.post(
        "/patients",
        json={"name": "Test User", "email": "test@hospital.io"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@hospital.io"
    assert "id" in data
    assert data["status"] == "created"


def test_register_existing_patient():
    # Register first time
    client.post("/patients", json={"name": "Duplicate", "email": "dup@hospital.io"})
    # Register second time
    response = client.post("/patients", json={"name": "Duplicate", "email": "dup@hospital.io"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "existing"


def test_upload_and_predict():
    # First, register a patient to get an ID
    reg_response = client.post("/patients", json={"name": "Analysis User", "email": "analysis@hospital.io"})
    patient_id = reg_response.json()["id"]

    # Mock feature data
    mock_features = {
        "TCGA_DESC": "LUAD",
        "GDSC Tissue descriptor 1": "lung",
        "Cancer Type (matching TCGA label)": "LUAD",
        "Screen Medium": "RPMI",
        "Gene Expression": "Y",
        "CNA": "Y",
        "Methylation": "Y"
    }

    # Test upload endpoint
    response = client.post(f"/patients/{patient_id}/upload", json=mock_features)
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "predictions" in data
    assert len(data["predictions"]) > 0

    # Verify prediction structure
    first_pred = data["predictions"][0]
    assert "drug_name" in first_pred
    assert "probability_sensitive" in first_pred
    assert "predicted_label" in first_pred


def test_doctor_dashboard_stats():
    # Setup some basic data
    reg_response = client.post("/patients", json={"name": "Doc View", "email": "doc@hospital.io"})
    patient_id = reg_response.json()["id"]
    client.post(f"/patients/{patient_id}/upload", json={"TCGA_DESC": "LUAD"})

    # Fetch dashboard
    response = client.get("/doctor/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    assert "patients" in data
    assert "stats" in data
    
    # Verify stats calculation
    stats = data["stats"]
    assert "total_patients" in stats
    assert "population_sensitivity" in stats
    assert "most_sensitive_drug" in stats
    assert "model_confidence" in stats
    
    # Since we uploaded one patient, total_patients should be >= 1
    assert stats["total_patients"] >= 1
