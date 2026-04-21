from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="IR License API", version="1.0.0")

# Temporary in-memory license storage
LICENSES = {
    "IR-ONLINE-TEST-001": {
        "is_active": True,
        "expiry_date": "2026-12-31",
        "license_type": "PRO"
    },
    "IR-ONLINE-TEST-002": {
        "is_active": False,
        "expiry_date": "2026-12-31",
        "license_type": "PRO"
    }
}

class LicenseValidationRequest(BaseModel):
    license_key: str
    plugin_name: Optional[str] = None
    plugin_version: Optional[str] = None

class LicenseValidationResponse(BaseModel):
    valid: bool
    message: str
    expiry_date: Optional[str] = None
    license_type: Optional[str] = None

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "IR License API"
    }

@app.post("/validate", response_model=LicenseValidationResponse)
def validate_license(req: LicenseValidationRequest):
    key = req.license_key.strip()

    if key not in LICENSES:
        return LicenseValidationResponse(
            valid=False,
            message="License key not found.",
            expiry_date=None,
            license_type=None
        )

    record = LICENSES[key]

    if not record["is_active"]:
        return LicenseValidationResponse(
            valid=False,
            message="License is inactive.",
            expiry_date=record["expiry_date"],
            license_type=record["license_type"]
        )

    return LicenseValidationResponse(
        valid=True,
        message="License is valid.",
        expiry_date=record["expiry_date"],
        license_type=record["license_type"]
    )