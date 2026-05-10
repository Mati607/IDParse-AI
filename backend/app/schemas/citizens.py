"""Request and response models for citizen (portal profile) API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateCitizenRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=500)
    email: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=80)
    preferred_language: str | None = Field(default=None, max_length=80)
    case_reference: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=8000)


class PatchCitizenRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=80)
    preferred_language: str | None = Field(default=None, max_length=80)
    case_reference: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=8000)


class CitizenListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
