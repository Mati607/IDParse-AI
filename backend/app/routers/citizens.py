"""
HTTP API for citizen profiles (portal case management).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app import citizen_repository as citizen_repo
from app import session_repository as session_repo
from app.schemas.citizens import CitizenListResponse, CreateCitizenRequest, PatchCitizenRequest

router = APIRouter()


@router.post("", status_code=201)
def create_citizen(body: CreateCitizenRequest) -> dict[str, Any]:
    cid = citizen_repo.create_citizen(
        display_name=body.display_name,
        email=body.email,
        phone=body.phone,
        preferred_language=body.preferred_language,
        case_reference=body.case_reference,
        status=body.status,
        notes=body.notes,
    )
    row = citizen_repo.get_citizen(cid)
    assert row is not None
    return row


@router.get("", response_model=CitizenListResponse)
def list_citizens(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=500),
    status: str | None = Query(None, max_length=32),
) -> CitizenListResponse:
    items, total = citizen_repo.list_citizens(limit=limit, offset=offset, q=q, status=status)
    return CitizenListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{citizen_id}")
def get_citizen(
    citizen_id: str,
    include_sessions: bool = Query(False),
    session_limit: int = Query(30, ge=1, le=100),
) -> dict[str, Any]:
    row = citizen_repo.get_citizen(citizen_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Citizen not found.")
    if not include_sessions:
        return row
    sessions, _ = session_repo.list_sessions(limit=session_limit, offset=0, citizen_id=citizen_id)
    return {**row, "sessions": sessions}


@router.patch("/{citizen_id}")
def patch_citizen(citizen_id: str, body: PatchCitizenRequest) -> dict[str, Any]:
    ok = citizen_repo.update_citizen(
        citizen_id,
        display_name=body.display_name,
        email=body.email,
        phone=body.phone,
        preferred_language=body.preferred_language,
        case_reference=body.case_reference,
        status=body.status,
        notes=body.notes,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Citizen not found.")
    row = citizen_repo.get_citizen(citizen_id)
    assert row is not None
    return row


@router.delete("/{citizen_id}", status_code=204, response_model=None)
def delete_citizen(citizen_id: str) -> None:
    if not citizen_repo.delete_citizen(citizen_id):
        raise HTTPException(status_code=404, detail="Citizen not found.")
