from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import secrets
import psycopg2

app = FastAPI(title="IR License API", version="2.0.0")

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            license_key TEXT PRIMARY KEY,
            is_active BOOLEAN NOT NULL,
            expiry_date TEXT,
            license_type TEXT
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


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


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return {"status": "ok", "service": "IR License API"}


@app.post("/validate", response_model=LicenseValidationResponse)
def validate_license(req: LicenseValidationRequest):
    key = req.license_key.strip()

    print(
        f"VALIDATE called: key={key}, "
        f"plugin={req.plugin_name}, "
        f"version={req.plugin_version}"
    )

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT is_active, expiry_date, license_type FROM licenses WHERE license_key = %s",
        (key,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return LicenseValidationResponse(
            valid=False,
            message="License key not found.",
            expiry_date=None,
            license_type=None
        )

    is_active, expiry_date, license_type = row

    if not is_active:
        return LicenseValidationResponse(
            valid=False,
            message="License is inactive.",
            expiry_date=expiry_date,
            license_type=license_type
        )

    return LicenseValidationResponse(
        valid=True,
        message="License is valid.",
        expiry_date=expiry_date,
        license_type=license_type
    )


@app.get("/licenses")
def list_licenses():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT license_key, is_active, expiry_date, license_type
        FROM licenses
        ORDER BY license_key
    """)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {
        row[0]: {
            "is_active": row[1],
            "expiry_date": row[2],
            "license_type": row[3]
        }
        for row in rows
    }


@app.post("/licenses/create", response_model=CreateLicenseResponse)
def create_license(req: CreateLicenseRequest):
    conn = get_connection()
    cur = conn.cursor()

    while True:
        key = "IR-" + secrets.token_hex(8).upper()
        cur.execute("SELECT 1 FROM licenses WHERE license_key = %s", (key,))
        if not cur.fetchone():
            break

    cur.execute("""
        INSERT INTO licenses (license_key, is_active, expiry_date, license_type)
        VALUES (%s, %s, %s, %s)
    """, (
        key,
        req.is_active,
        req.expiry_date,
        req.license_type.upper()
    ))

    conn.commit()
    cur.close()
    conn.close()

    return CreateLicenseResponse(
        license_key=key,
        message="License created successfully.",
        expiry_date=req.expiry_date,
        license_type=req.license_type.upper(),
        is_active=req.is_active
    )


@app.post("/licenses/disable")
def disable_license(req: DisableLicenseRequest):
    key = req.license_key.strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM licenses WHERE license_key = %s", (key,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="License key not found.")

    cur.execute(
        "UPDATE licenses SET is_active = FALSE WHERE license_key = %s",
        (key,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {
        "message": "License disabled successfully.",
        "license_key": key
    }


@app.post("/licenses/enable")
def enable_license(req: EnableLicenseRequest):
    key = req.license_key.strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM licenses WHERE license_key = %s", (key,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="License key not found.")

    cur.execute(
        "UPDATE licenses SET is_active = TRUE WHERE license_key = %s",
        (key,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {
        "message": "License enabled successfully.",
        "license_key": key
    }


@app.post("/licenses/delete")
def delete_license(req: DeleteLicenseRequest):
    key = req.license_key.strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM licenses WHERE license_key = %s", (key,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="License key not found.")

    cur.execute(
        "DELETE FROM licenses WHERE license_key = %s",
        (key,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {
        "message": "License deleted successfully.",
        "license_key": key
    }