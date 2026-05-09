import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    backend_dir = Path(__file__).resolve().parent.parent
    load_dotenv(backend_dir / ".env")
    load_dotenv(backend_dir.parent / ".env")
except ImportError:
    pass

from fastapi import Body, FastAPI, File, Form, Query, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, GOOGLE_API_KEY
from app.extraction import (
    extract_from_passport_file,
    extract_from_g28_file,
    merge_extracted,
    validate_passport_file,
    validate_g28_file,
)
from app.db import init_db
from app.form_filler import fill_form
from app.extraction_quality import build_readiness_report
from app.extraction_quality.rule_catalog import export_catalog_payload
from app.preview_fill import build_fill_preview, normalize_merged_extracted
from app.demo_samples import sample_merged_extraction
from app.extraction_compare import compare_extractions_extended
from app.routers import extraction_sessions
from app.intake.router import router as intake_router
from app.intake.retention import sweep_intake_retention


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sweep_intake_retention()
    yield


app = FastAPI(
    title="FormPilot – AI Document-to-Form Demo",
    version="0.2.0",
    lifespan=lifespan,
)

_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_extra = [o.strip() for o in (ALLOWED_ORIGINS or "").split(",") if o.strip()]
_cors_origins = list(dict.fromkeys(_default_origins + _extra))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    extraction_sessions.router,
    prefix="/extraction-sessions",
    tags=["extraction-sessions"],
)
app.include_router(intake_router, prefix="/intake", tags=["intake"])

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}


def check_api_key():
    if not GOOGLE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY is not set. Set it in .env for document extraction.",
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/preview-fill")
def preview_fill(body: dict = Body(...)):
    """
    Return which form-mapped fields have non-empty values for the given merged extraction.

    No browser and no Gemini calls; mirrors the label/value pairs Playwright would try to fill.
    """
    normalized = normalize_merged_extracted(body if isinstance(body, dict) else {})
    return build_fill_preview(normalized)


@app.post("/compare-extractions")
def compare_extractions_endpoint(body: dict = Body(...)):
    """
    Compare two merged extraction payloads (passport + attorney dicts).

    Returns per-field deltas for mapped form keys, fingerprints, unmapped keys, and a short narrative.
    Request JSON: { \"left\": {...}, \"right\": {...}, \"label_left\": optional, \"label_right\": optional }.
    """
    if not isinstance(body, dict):
        body = {}
    left = body.get("left") if isinstance(body.get("left"), dict) else {}
    right = body.get("right") if isinstance(body.get("right"), dict) else {}
    label_left = body.get("label_left") if isinstance(body.get("label_left"), str) else None
    label_right = body.get("label_right") if isinstance(body.get("label_right"), str) else None
    return compare_extractions_extended(
        left,
        right,
        label_left=label_left,
        label_right=label_right,
    )


@app.get("/extraction-quality/rules")
def extraction_quality_rules():
    """
    Static catalog of readiness rule codes with titles, categories, and remediation text.

    Useful for UI tooltips and offline documentation; no extraction input required.
    """
    return export_catalog_payload()


@app.post("/extraction-readiness")
def extraction_readiness(
    body: dict = Body(...),
    catalog: bool = Query(
        False,
        description="If true, each finding includes a catalog block with remediation metadata.",
    ),
):
    """
    Rule-based readiness report for a merged extraction (passport + attorney).

    No LLM calls: scores completeness and flags likely data issues (e.g. expired passport).
    """
    normalized = normalize_merged_extracted(body if isinstance(body, dict) else {})
    return build_readiness_report(normalized, attach_rule_catalog=catalog)


@app.get("/demo/sample-extraction")
def demo_sample_extraction(variant: str = "good"):
    """
    Return a demo merged extraction + readiness + fill preview without any external API calls.
    """
    merged = sample_merged_extraction(variant=variant)
    normalized = normalize_merged_extracted(merged)
    readiness = build_readiness_report(normalized)
    preview = build_fill_preview(normalized)
    return {"extracted": merged, "readiness": readiness, "preview_fill": preview}


@app.post("/demo/sample-session", status_code=201)
def demo_create_sample_session(variant: str = "good"):
    """
    Create and persist a demo extraction session without any external API calls.
    """
    merged = sample_merged_extraction(variant=variant)
    normalized = normalize_merged_extracted(merged)
    readiness = build_readiness_report(normalized)
    from app import session_repository as session_repo

    sid = session_repo.create_session(
        normalized,
        title=f"Demo session ({variant})",
        passport_filename="demo-passport.png",
        g28_filename="demo-g28.png",
        notes="Generated locally for demos; no external API calls.",
        quality_snapshot=readiness,
    )
    return {"id": sid, "readiness": readiness, "extracted": normalized}


def _validation_error_response(validation_errors: dict) -> tuple[int, dict]:
    """Build status code and JSON body for validation failures so the user sees which documents are invalid."""
    messages = []
    if validation_errors.get("passport"):
        messages.append(f"Passport: {validation_errors['passport']}")
    if validation_errors.get("g28"):
        messages.append(f"G-28: {validation_errors['g28']}")
    detail_text = " ".join(messages) if messages else "The uploaded document(s) are not valid."
    body = {"detail": detail_text, "validation_errors": dict(validation_errors)}
    return 400, body


@app.post("/extract")
async def extract(
    passport: Optional[UploadFile] = File(None),
    g28: Optional[UploadFile] = File(None),
):
    check_api_key()
    if not passport and not g28:
        raise HTTPException(status_code=400, detail="Upload at least one file: passport or g28.")

    validation_errors: dict = {}
    passport_data: dict = {}
    g28_data: dict = {}

    if passport:
        ct = passport.content_type or ""
        if ct not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Passport file must be PDF or image (JPEG/PNG). Got: {ct}",
            )
        raw = await passport.read()
        val = await validate_passport_file(raw, ct)
        if not val.get("is_valid"):
            validation_errors["passport"] = val.get("reason") or "This document does not appear to be a passport."
        else:
            passport_data = await extract_from_passport_file(raw, ct)

    if g28:
        ct = g28.content_type or ""
        if ct not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"G-28 file must be PDF or image (JPEG/PNG). Got: {ct}",
            )
        raw = await g28.read()
        val = await validate_g28_file(raw, ct)
        if not val.get("is_valid"):
            validation_errors["g28"] = val.get("reason") or "This document does not appear to be Form G-28/A-28."
        else:
            g28_data = await extract_from_g28_file(raw, ct)

    if validation_errors:
        status, body = _validation_error_response(validation_errors)
        raise HTTPException(status_code=status, detail=body)

    merged = merge_extracted(passport_data, g28_data)
    return merged


@app.post("/fill-form")
async def fill_form_endpoint(
    form_url: str = Form(..., description="URL of the form to open and fill"),
    passport: Optional[UploadFile] = File(None),
    g28: Optional[UploadFile] = File(None),
):
    check_api_key()
    form_url = (form_url or "").strip()
    if not form_url:
        raise HTTPException(status_code=400, detail="form_url is required.")
    if not form_url.startswith("http://") and not form_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="form_url must be http or https.")
    if not passport and not g28:
        raise HTTPException(status_code=400, detail="Upload at least one file: passport or g28.")

    validation_errors = {}
    passport_data = {}
    g28_data = {}

    if passport:
        ct = passport.content_type or ""
        if ct not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid passport file type: {ct}")
        raw = await passport.read()
        val = await validate_passport_file(raw, ct)
        if not val.get("is_valid"):
            validation_errors["passport"] = val.get("reason") or "This document does not appear to be a passport."
        else:
            passport_data = await extract_from_passport_file(raw, ct)

    if g28:
        ct = g28.content_type or ""
        if ct not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid G-28 file type: {ct}")
        raw = await g28.read()
        val = await validate_g28_file(raw, ct)
        if not val.get("is_valid"):
            validation_errors["g28"] = val.get("reason") or "This document does not appear to be Form G-28/A-28."
        else:
            g28_data = await extract_from_g28_file(raw, ct)

    if validation_errors:
        status, body = _validation_error_response(validation_errors)
        raise HTTPException(status_code=status, detail=body)

    merged = merge_extracted(passport_data, g28_data)
    result = await fill_form(merged, form_url=form_url)
    return {
        "extracted": merged,
        "filled_fields": result["filled"],
        "errors": result["errors"],
        "form_url": result["url"],
        "opened_in_existing_browser": result.get("opened_in_existing_browser", False),
    }


def run():
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
