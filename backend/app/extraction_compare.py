"""
Structural comparison of two merged extraction payloads (passport + attorney).

Pure functions: no database or network. Used for QA when re-running extraction or
comparing intake overrides to an earlier model output.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

from app.field_mappings import list_sections_and_keys
from app.preview_fill import normalize_merged_extracted

ChangeKind = Literal["unchanged", "changed", "left_only", "right_only", "both_empty"]


def _non_empty_scalar(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (dict, list)):
        return bool(v)
    return bool(str(v).strip())


def normalize_compare_scalar(v: Any) -> str:
    """
    Normalize values for fuzzy equality: trim, lowercase, collapse internal whitespace,
    strip combining marks, and remove most punctuation.
    """
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return ""
    s = unicodedata.normalize("NFKD", str(v))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9@._+\-]+", "", s)
    return s


def stable_fingerprint(extracted: dict[str, Any]) -> str:
    """SHA-256 hex digest of normalized merged extraction (sorted JSON-like walk)."""
    norm = normalize_merged_extracted(extracted)

    def _walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _walk(obj[k]) for k in sorted(obj.keys())}
        if isinstance(obj, list):
            return [_walk(x) for x in obj]
        if obj is None:
            return None
        if isinstance(obj, (int, float, bool)):
            return obj
        return normalize_compare_scalar(obj)

    import json

    payload = json.dumps(_walk(norm), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class FieldDelta:
    section: str
    key: str
    field_id: str
    kind: ChangeKind
    left_raw: Any = None
    right_raw: Any = None
    left_normalized: str = ""
    right_normalized: str = ""
    notes: list[str] = field(default_factory=list)


def _classify(left_val: Any, right_val: Any) -> ChangeKind:
    le = _non_empty_scalar(left_val)
    re_ = _non_empty_scalar(right_val)
    if not le and not re_:
        return "both_empty"
    if le and not re_:
        return "left_only"
    if re_ and not le:
        return "right_only"
    ln = normalize_compare_scalar(left_val)
    rn = normalize_compare_scalar(right_val)
    if ln == rn:
        return "unchanged"
    return "changed"


def diff_mapped_fields(left: dict[str, Any], right: dict[str, Any]) -> list[FieldDelta]:
    """
    Compare mapped passport/attorney keys in FIELD_MAPPINGS order.

    left and right should be merged shapes; they are normalized before read.
    """
    l0 = normalize_merged_extracted(left)
    r0 = normalize_merged_extracted(right)
    lp, la = l0.get("passport") or {}, l0.get("attorney") or {}
    rp, ra = r0.get("passport") or {}, r0.get("attorney") or {}
    out: list[FieldDelta] = []
    for section, key in list_sections_and_keys():
        lsrc = lp if section == "passport" else la
        rsrc = rp if section == "passport" else ra
        lv = lsrc.get(key) if isinstance(lsrc, dict) else None
        rv = rsrc.get(key) if isinstance(rsrc, dict) else None
        kind = _classify(lv, rv)
        delta = FieldDelta(
            section=section,
            key=key,
            field_id=f"{section}.{key}",
            kind=kind,
            left_raw=lv,
            right_raw=rv,
            left_normalized=normalize_compare_scalar(lv) if _non_empty_scalar(lv) else "",
            right_normalized=normalize_compare_scalar(rv) if _non_empty_scalar(rv) else "",
        )
        if kind == "changed" and str(lv).strip() != str(rv).strip():
            delta.notes.append("String form differs after trim (normalization may still collapse to equal).")
        out.append(delta)
    return out


def summarize_deltas(deltas: list[FieldDelta]) -> dict[str, Any]:
    counts: dict[str, int] = {
        "unchanged": 0,
        "changed": 0,
        "left_only": 0,
        "right_only": 0,
        "both_empty": 0,
    }
    for d in deltas:
        counts[d.kind] = counts.get(d.kind, 0) + 1
    material = counts["changed"] + counts["left_only"] + counts["right_only"]
    return {
        "fields_compared": len(deltas),
        "material_differences": material,
        "by_kind": counts,
    }


def deltas_to_json(deltas: list[FieldDelta]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for d in deltas:
        rows.append(
            {
                "section": d.section,
                "key": d.key,
                "field_id": d.field_id,
                "kind": d.kind,
                "left": d.left_raw,
                "right": d.right_raw,
                "left_normalized": d.left_normalized or None,
                "right_normalized": d.right_normalized or None,
                "notes": list(d.notes),
            }
        )
    return rows


def compare_extractions(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    label_left: str | None = None,
    label_right: str | None = None,
) -> dict[str, Any]:
    """
    Full comparison payload for HTTP responses.

    Includes fingerprints, per-field deltas for mapped keys, and aggregate stats.
    """
    deltas = diff_mapped_fields(left, right)
    summary = summarize_deltas(deltas)
    fp_l = stable_fingerprint(left)
    fp_r = stable_fingerprint(right)
    return {
        "schema_version": 1,
        "labels": {"left": label_left, "right": label_right},
        "fingerprints": {"left": fp_l, "right": fp_r, "identical": fp_l == fp_r},
        "summary": summary,
        "deltas": [d for d in deltas_to_json(deltas) if d["kind"] != "both_empty" or False],
    }


def compare_extractions_full(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    label_left: str | None = None,
    label_right: str | None = None,
    include_empty: bool = False,
) -> dict[str, Any]:
    """Like compare_extractions but can include both_empty rows for spreadsheets."""
    base = compare_extractions(left, right, label_left=label_left, label_right=label_right)
    if include_empty:
        base["deltas"] = deltas_to_json(diff_mapped_fields(left, right))
    return base


# ---------------------------------------------------------------------------
# Narrative helpers (human-readable summaries for logs and UI)
# ---------------------------------------------------------------------------

_SEVERITY_RANK = {"changed": 3, "left_only": 2, "right_only": 2, "unchanged": 0, "both_empty": 0}


def _delta_severity(kind: ChangeKind) -> int:
    return _SEVERITY_RANK.get(kind, 0)


def narrative_top_deltas(deltas: list[FieldDelta], *, limit: int = 12) -> list[str]:
    """Short bullet lines for the largest practical differences."""
    interesting = [d for d in deltas if _delta_severity(d.kind) >= 2]
    interesting.sort(key=lambda d: (-_delta_severity(d.kind), d.section, d.key))
    lines: list[str] = []
    for d in interesting[:limit]:
        if d.kind == "changed":
            lines.append(
                f"{d.field_id}: {d.left_raw!r} → {d.right_raw!r}"
            )
        elif d.kind == "left_only":
            lines.append(f"{d.field_id}: only in left ({d.left_raw!r})")
        elif d.kind == "right_only":
            lines.append(f"{d.field_id}: only in right ({d.right_raw!r})")
    return lines


def compare_with_narrative(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    label_left: str | None = None,
    label_right: str | None = None,
) -> dict[str, Any]:
    """compare_extractions plus a concise narrative list."""
    deltas = diff_mapped_fields(left, right)
    payload = compare_extractions(left, right, label_left=label_left, label_right=label_right)
    payload["narrative"] = narrative_top_deltas(deltas)
    return payload


# ---------------------------------------------------------------------------
# Section-level rollups (coarse signal for dashboards)
# ---------------------------------------------------------------------------

def section_rollup(deltas: list[FieldDelta]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for d in deltas:
        bucket = out.setdefault(d.section, {"changed": 0, "left_only": 0, "right_only": 0, "unchanged": 0, "both_empty": 0})
        bucket[d.kind] = bucket.get(d.kind, 0) + 1
    return out


def compare_extractions_with_sections(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    label_left: str | None = None,
    label_right: str | None = None,
) -> dict[str, Any]:
    deltas = diff_mapped_fields(left, right)
    payload = compare_extractions(left, right, label_left=label_left, label_right=label_right)
    payload["by_section"] = section_rollup(deltas)
    return payload


# ---------------------------------------------------------------------------
# Extra keys outside FIELD_MAPPINGS (forward compatibility when BAML adds fields)
# ---------------------------------------------------------------------------

def _collect_keys(d: dict[str, Any], section: str) -> set[str]:
    sub = d.get(section)
    if not isinstance(sub, dict):
        return set()
    return set(str(k) for k in sub.keys())


def unmapped_key_diff(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Keys present in either payload but not part of FIELD_MAPPINGS for that section."""
    mapped_passport = {k for s, k in list_sections_and_keys() if s == "passport"}
    mapped_attorney = {k for s, k in list_sections_and_keys() if s == "attorney"}
    l0 = normalize_merged_extracted(left)
    r0 = normalize_merged_extracted(right)
    out: dict[str, Any] = {}
    for section, mapped in (("passport", mapped_passport), ("attorney", mapped_attorney)):
        lk = _collect_keys(l0, section) - mapped
        rk = _collect_keys(r0, section) - mapped
        out[section] = {
            "only_left": sorted(lk - rk),
            "only_right": sorted(rk - lk),
            "both": sorted(lk & rk),
        }
    return out


def compare_extractions_extended(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    label_left: str | None = None,
    label_right: str | None = None,
) -> dict[str, Any]:
    """Mapped deltas plus unmapped key presence and narrative."""
    payload = compare_with_narrative(left, right, label_left=label_left, label_right=label_right)
    payload["unmapped_keys"] = unmapped_key_diff(left, right)
    deltas = diff_mapped_fields(left, right)
    payload["by_section"] = section_rollup(deltas)
    return payload
