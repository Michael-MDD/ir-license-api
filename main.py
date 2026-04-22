from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import json
import os
import secrets

app = FastAPI(title="IR License API", version="1.2.0")

LICENSE_FILE = "licenses.json"


def load_licenses() -> Dict[str, dict]:
    if not os.path.exists(LICENSE_FILE):
        return {}

    with open(LICENSE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_licenses(data: Dict[str, dict]) -> None:
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class LicenseValidationRequest(BaseModel):
    license_key: str
    plugin_name: Optional[str] = None
    plugin_version: Optional[str] = None


class LicenseValidationResponse(BaseModel):
    valid: bool
    message: str
    expiry_date: Optional[str] = None
    license_type: Optional[str] = None


class CreateLicenseRequest(BaseModel):
    expiry_date: str
    license_type: str = "PRO"
    is_active: bool = True


class CreateLicenseResponse(BaseModel):
    license_key: str
    message: str
    expiry_date: str
    license_type: str
    is_active: bool


class DisableLicenseRequest(BaseModel):
    license_key: str


class EnableLicenseRequest(BaseModel):
    license_key: str


class DeleteLicenseRequest(BaseModel):
    license_key: str


@app.get("/")
def root():
    return {"status": "ok", "service": "IR License API"}


@app.post("/validate", response_model=LicenseValidationResponse)
def validate_license(req: LicenseValidationRequest):
    licenses = load_licenses()
    key = req.license_key.strip()

    print(
        f"VALIDATE called: key={key}, "
        f"plugin={req.plugin_name}, "
        f"version={req.plugin_version}"
    )

    if key not in licenses:
        return LicenseValidationResponse(
            valid=False,
            message="License key not found.",
            expiry_date=None,
            license_type=None
        )

    record = licenses[key]

    if not record.get("is_active", False):
        return LicenseValidationResponse(
            valid=False,
            message="License is inactive.",
            expiry_date=record.get("expiry_date"),
            license_type=record.get("license_type")
        )

    return LicenseValidationResponse(
        valid=True,
        message="License is valid.",
        expiry_date=record.get("expiry_date"),
        license_type=record.get("license_type")
    )


@app.get("/licenses")
def list_licenses():
    return load_licenses()


@app.post("/licenses/create", response_model=CreateLicenseResponse)
def create_license(req: CreateLicenseRequest):
    licenses = load_licenses()

    while True:
        key = "IR-" + secrets.token_hex(8).upper()
        if key not in licenses:
            break

    licenses[key] = {
        "is_active": req.is_active,
        "expiry_date": req.expiry_date,
        "license_type": req.license_type.upper()
    }

    save_licenses(licenses)

    return CreateLicenseResponse(
        license_key=key,
        message="License created successfully.",
        expiry_date=req.expiry_date,
        license_type=req.license_type.upper(),
        is_active=req.is_active
    )


@app.post("/licenses/disable")
def disable_license(req: DisableLicenseRequest):
    licenses = load_licenses()
    key = req.license_key.strip()

    if key not in licenses:
        raise HTTPException(status_code=404, detail="License key not found.")

    licenses[key]["is_active"] = False
    save_licenses(licenses)

    return {
        "message": "License disabled successfully.",
        "license_key": key
    }


@app.post("/licenses/enable")
def enable_license(req: EnableLicenseRequest):
    licenses = load_licenses()
    key = req.license_key.strip()

    if key not in licenses:
        raise HTTPException(status_code=404, detail="License key not found.")

    licenses[key]["is_active"] = True
    save_licenses(licenses)

    return {
        "message": "License enabled successfully.",
        "license_key": key
    }


@app.post("/licenses/delete")
def delete_license(req: DeleteLicenseRequest):
    licenses = load_licenses()
    key = req.license_key.strip()

    if key not in licenses:
        raise HTTPException(status_code=404, detail="License key not found.")

    del licenses[key]
    save_licenses(licenses)

    return {
        "message": "License deleted successfully.",
        "license_key": key
    }
}