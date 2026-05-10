"""
Request and response models for saved extraction sessions API.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MergedExtractionIn(BaseModel):
    """Merged passport + attorney payload as returned by POST /extract."""

    model_config = ConfigDict(extra="ignore")

    passport: dict[str, Any] = Field(default_factory=dict)
    attorney: dict[str, Any] = Field(default_factory=dict)


class CreateExtractionSessionRequest(BaseModel):
    extracted: MergedExtractionIn
    title: str | None = Field(default=None, max_length=500)
    passport_filename: str | None = Field(default=None, max_length=500)
    g28_filename: str | None = Field(default=None, max_length=500)
    default_form_url: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=5000)
    citizen_id: str | None = Field(default=None, max_length=64)
    tags: list[str] | None = Field(default=None, max_length=25)

    @field_validator("tags")
    @classmethod
    def _validate_tag_items(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        for t in v:
            if t is not None and len(t) > 64:
                raise ValueError("Each tag must be at most 64 characters.")
        return v


class PatchExtractionSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=5000)
    default_form_url: str | None = Field(default=None, max_length=2000)
    citizen_id: str | None = Field(default=None, max_length=64)
    tags: list[str] | None = Field(default=None, max_length=25)

    @field_validator("tags")
    @classmethod
    def _validate_tag_items_patch(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        for t in v:
            if t is not None and len(t) > 64:
                raise ValueError("Each tag must be at most 64 characters.")
        return v


class FillStoredSessionFormRequest(BaseModel):
    form_url: str = Field(..., min_length=1, max_length=2000)


class ExtractionSessionListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
