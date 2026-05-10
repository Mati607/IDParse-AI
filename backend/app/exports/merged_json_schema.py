"""
JSON Schema (draft-07 style) describing merged passport + attorney extraction payloads.

Suitable for client validation, OpenAPI-adjacent documentation, and contract tests.
"""

from __future__ import annotations

from typing import Any

_PASSPORT_PROPS: dict[str, Any] = {
    "last_name": {
        "type": ["string", "null"],
        "description": "Family name as shown on the passport data page (surname).",
        "examples": ["Doe", "García López"],
    },
    "first_name": {
        "type": ["string", "null"],
        "description": "Given name(s) including any second given names printed on the document.",
        "examples": ["Jane", "Mohammed Ali"],
    },
    "middle_name": {
        "type": ["string", "null"],
        "description": "Middle name(s) or patronymic segment if separated on the data page.",
    },
    "passport_number": {
        "type": ["string", "null"],
        "description": "Machine-readable or printed passport / travel document number.",
        "pattern": "^[A-Za-z0-9\\-]{0,32}$",
    },
    "country_of_issue": {
        "type": ["string", "null"],
        "description": "Issuing authority country name or code as printed (not necessarily ISO-normalized).",
    },
    "nationality": {
        "type": ["string", "null"],
        "description": "Nationality / citizenship field as printed; may differ from place of birth.",
    },
    "date_of_birth": {
        "type": ["string", "null"],
        "description": "Date of birth string as extracted; parsers accept ISO and common locale formats.",
        "examples": ["1990-01-15", "15 JAN 1990"],
    },
    "place_of_birth": {
        "type": ["string", "null"],
        "description": "City, region, and/or country of birth as printed on the passport.",
    },
    "sex": {
        "type": ["string", "null"],
        "description": "Sex or gender marker field (often M/F/X on ICAO documents).",
        "maxLength": 16,
    },
    "date_of_issue": {
        "type": ["string", "null"],
        "description": "Issue date of the passport as printed.",
    },
    "date_of_expiration": {
        "type": ["string", "null"],
        "description": "Expiration date; readiness checks compare against UTC 'today' heuristically.",
    },
}

_ATTORNEY_PROPS: dict[str, Any] = {
    "online_account_number": {
        "type": ["string", "null"],
        "description": "USCIS online account number if present on the representative form.",
    },
    "family_name": {
        "type": ["string", "null"],
        "description": "Attorney or accredited representative family (last) name.",
    },
    "given_name": {
        "type": ["string", "null"],
        "description": "Attorney given (first) name.",
    },
    "middle_name": {
        "type": ["string", "null"],
        "description": "Attorney middle name or initial if captured.",
    },
    "street_number_and_name": {
        "type": ["string", "null"],
        "description": "Mailing street address line for the representative.",
    },
    "apt_ste_flr": {
        "type": ["string", "null"],
        "description": "Unit, suite, apartment, floor, or building identifier.",
    },
    "city": {
        "type": ["string", "null"],
        "description": "Mailing city.",
    },
    "state": {
        "type": ["string", "null"],
        "description": "State, province, or region; may be abbreviated.",
    },
    "zip_code": {
        "type": ["string", "null"],
        "description": "Postal or ZIP code including extensions when printed.",
    },
    "country": {
        "type": ["string", "null"],
        "description": "Mailing country as printed on the G-28 (or equivalent).",
    },
    "daytime_telephone": {
        "type": ["string", "null"],
        "description": "Primary daytime telephone with formatting as extracted.",
    },
    "mobile_telephone": {
        "type": ["string", "null"],
        "description": "Mobile telephone if distinct from daytime number.",
    },
    "email": {
        "type": ["string", "null"],
        "description": "Representative email for agency correspondence.",
        "format": "email",
    },
    "licensing_authority": {
        "type": ["string", "null"],
        "description": "Bar or licensing authority that issued the attorney credentials.",
    },
    "bar_number": {
        "type": ["string", "null"],
        "description": "Attorney registration or bar number as printed.",
    },
    "law_firm_or_organization": {
        "type": ["string", "null"],
        "description": "Law firm or organization name associated with the representative.",
    },
}

_READINESS_FINDING: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "severity": {"type": "string", "enum": ["error", "warn", "info"]},
        "code": {"type": "string"},
        "field": {"type": "string"},
        "message": {"type": "string"},
        "catalog": {"type": ["object", "null"]},
    },
    "required": ["severity", "message"],
}

_READINESS_SNAPSHOT: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "schema_version": {"type": "integer"},
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "grade": {"type": "string"},
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": _READINESS_FINDING},
        "counts": {
            "type": "object",
            "additionalProperties": True,
        },
        "generated_at": {"type": "string"},
    },
}

_LAST_FILL: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "filled": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        "errors": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        "form_url": {"type": "string"},
        "opened_in_existing_browser": {"type": "boolean"},
    },
}

_SESSION_ENVELOPE: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://example.com/schemas/idparse/extraction-session.json",
    "title": "IDParse extraction session export",
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "id": {
            "type": "string",
            "description": "Opaque session identifier (UUID string).",
        },
        "created_at": {
            "type": "string",
            "description": "ISO-8601 timestamp when the session row was created.",
        },
        "updated_at": {
            "type": "string",
            "description": "ISO-8601 timestamp of the last metadata or extraction update.",
        },
        "title": {
            "type": ["string", "null"],
            "description": "Human-friendly label shown in session lists.",
        },
        "passport_filename": {
            "type": ["string", "null"],
            "description": "Original upload filename for the passport artifact, if any.",
        },
        "g28_filename": {
            "type": ["string", "null"],
            "description": "Original upload filename for the G-28 artifact, if any.",
        },
        "default_form_url": {
            "type": ["string", "null"],
            "description": "Optional default HTML form URL suggested for Playwright fill.",
        },
        "notes": {
            "type": ["string", "null"],
            "description": "Free-form operator notes stored with the session.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string", "maxLength": 48},
            "maxItems": 20,
            "description": "Normalized lowercase labels for organizing and filtering saved sessions.",
        },
        "citizen_id": {
            "type": ["string", "null"],
            "description": "Linked portal citizen profile id, if assigned.",
        },
        "citizen_display_name": {
            "type": ["string", "null"],
            "description": "Display name of the linked citizen at export time (informational).",
        },
        "extracted": {
            "type": "object",
            "additionalProperties": False,
            "description": "Merged BAML extraction output for passport and attorney sections.",
            "properties": {
                "passport": {
                    "type": "object",
                    "additionalProperties": False,
                    "description": "Passport / travel document fields mapped to form labels.",
                    "properties": _PASSPORT_PROPS,
                },
                "attorney": {
                    "type": "object",
                    "additionalProperties": False,
                    "description": "G-28 representative block mapped to form labels.",
                    "properties": _ATTORNEY_PROPS,
                },
            },
            "required": ["passport", "attorney"],
        },
        "readiness": {
            "description": "Snapshot of rule-based readiness at save time (or last recompute).",
            **_READINESS_SNAPSHOT,
        },
        "last_fill": {
            "description": "Summary of the most recent Playwright fill attempt, if any.",
            **_LAST_FILL,
        },
    },
    "required": ["id", "extracted"],
}

_MERGED_ONLY: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://example.com/schemas/idparse/merged-extraction.json",
    "title": "Merged passport + attorney extraction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "passport": _SESSION_ENVELOPE["properties"]["extracted"]["properties"]["passport"],
        "attorney": _SESSION_ENVELOPE["properties"]["extracted"]["properties"]["attorney"],
    },
    "required": ["passport", "attorney"],
}


def merged_extraction_schema(*, envelope: bool = False) -> dict[str, Any]:
    """
    Return a deep-copied JSON Schema dict.

    Args:
        envelope: If True, include session metadata wrapper (export shape). If False, only merged extraction.
    """
    import copy

    return copy.deepcopy(_SESSION_ENVELOPE if envelope else _MERGED_ONLY)


def schema_bundle() -> dict[str, Any]:
    """Payload for HTTP: merged shape plus full session export shape."""
    import copy

    return {
        "schema_version": 1,
        "json_schema_draft": "draft-07",
        "merged_extraction": copy.deepcopy(_MERGED_ONLY),
        "session_export": copy.deepcopy(_SESSION_ENVELOPE),
        "notes": [
            "All string fields are nullable to match optional BAML outputs.",
            "Readiness and last_fill objects allow additionalProperties for forward compatibility.",
        ],
    }
