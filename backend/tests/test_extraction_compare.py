"""Tests for merged extraction comparison and /compare-extractions API."""

import pytest
from fastapi.testclient import TestClient

from app.extraction_compare import (
    compare_extractions,
    compare_extractions_extended,
    compare_extractions_full,
    compare_extractions_with_sections,
    compare_with_narrative,
    diff_mapped_fields,
    narrative_top_deltas,
    normalize_compare_scalar,
    stable_fingerprint,
    summarize_deltas,
    unmapped_key_diff,
)
from app.main import app


class TestNormalizeCompareScalar:
    def test_trims_and_lowercases(self):
        assert normalize_compare_scalar("  Hello ") == "hello"

    def test_strips_punctuation_heuristic(self):
        assert normalize_compare_scalar("Doe,") == "doe"
        assert normalize_compare_scalar("a@b.co") == "a@b.co"

    def test_none_empty(self):
        assert normalize_compare_scalar(None) == ""


class TestStableFingerprint:
    def test_identical_payloads(self):
        p = {"passport": {"last_name": "Lee"}, "attorney": {"city": "Boston"}}
        assert stable_fingerprint(p) == stable_fingerprint(dict(p))

    def test_order_insensitive_section_keys(self):
        a = {"passport": {"a": "1", "b": "2"}, "attorney": {}}
        b = {"attorney": {}, "passport": {"b": "2", "a": "1"}}
        assert stable_fingerprint(a) == stable_fingerprint(b)


class TestDiffMappedFields:
    def test_changed_kind(self):
        left = {"passport": {"last_name": "A"}, "attorney": {}}
        right = {"passport": {"last_name": "B"}, "attorney": {}}
        deltas = diff_mapped_fields(left, right)
        row = next(d for d in deltas if d.field_id == "passport.last_name")
        assert row.kind == "changed"

    def test_left_only(self):
        left = {"passport": {"first_name": "Z"}, "attorney": {}}
        right = {"passport": {}, "attorney": {}}
        deltas = diff_mapped_fields(left, right)
        row = next(d for d in deltas if d.field_id == "passport.first_name")
        assert row.kind == "left_only"

    def test_right_only(self):
        left = {"passport": {}, "attorney": {}}
        right = {"passport": {}, "attorney": {"email": "x@y.z"}}
        deltas = diff_mapped_fields(left, right)
        row = next(d for d in deltas if d.field_id == "attorney.email")
        assert row.kind == "right_only"

    def test_unchanged_normalized_equal(self):
        left = {"passport": {"last_name": "  DOE "}, "attorney": {}}
        right = {"passport": {"last_name": "doe"}, "attorney": {}}
        deltas = diff_mapped_fields(left, right)
        row = next(d for d in deltas if d.field_id == "passport.last_name")
        assert row.kind == "unchanged"

    def test_both_empty(self):
        deltas = diff_mapped_fields({"passport": {}, "attorney": {}}, {"passport": {}, "attorney": {}})
        assert all(d.kind == "both_empty" for d in deltas)


class TestSummaries:
    def test_summarize_counts(self):
        left = {"passport": {"last_name": "A", "first_name": "B"}, "attorney": {}}
        right = {"passport": {"last_name": "A", "first_name": "C"}, "attorney": {}}
        deltas = diff_mapped_fields(left, right)
        s = summarize_deltas(deltas)
        assert s["material_differences"] >= 1
        assert s["by_kind"]["changed"] >= 1


class TestNarrative:
    def test_narrative_lists_changes(self):
        left = {"passport": {"last_name": "A"}, "attorney": {}}
        right = {"passport": {"last_name": "B"}, "attorney": {}}
        deltas = diff_mapped_fields(left, right)
        lines = narrative_top_deltas(deltas, limit=5)
        assert any("passport.last_name" in ln for ln in lines)


class TestCompareExtractionsHttp:
    def test_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/compare-extractions",
            json={
                "left": {"passport": {"last_name": "A"}, "attorney": {}},
                "right": {"passport": {"last_name": "B"}, "attorney": {}},
                "label_left": "v1",
                "label_right": "v2",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["fingerprints"]["identical"] is False
        assert data["labels"]["left"] == "v1"
        assert "unmapped_keys" in data
        assert "by_section" in data
        kinds = {d["kind"] for d in data["deltas"]}
        assert "changed" in kinds


class TestExtendedHelpers:
    def test_compare_with_sections(self):
        out = compare_extractions_with_sections(
            {"passport": {"last_name": "A"}, "attorney": {}},
            {"passport": {"last_name": "B"}, "attorney": {}},
        )
        assert "passport" in out["by_section"]

    def test_compare_with_narrative(self):
        out = compare_with_narrative(
            {"passport": {"last_name": "A"}, "attorney": {}},
            {"passport": {"last_name": "B"}, "attorney": {}},
        )
        assert isinstance(out["narrative"], list)

    def test_unmapped_keys(self):
        left = {"passport": {"last_name": "A", "custom_note": "x"}, "attorney": {}}
        right = {"passport": {"last_name": "A"}, "attorney": {"extra": "y"}}
        u = unmapped_key_diff(left, right)
        assert "custom_note" in u["passport"]["only_left"] or "extra" in u["attorney"]["only_right"]

    def test_full_includes_empty(self):
        out = compare_extractions_full(
            {"passport": {}, "attorney": {}},
            {"passport": {}, "attorney": {}},
            include_empty=True,
        )
        assert len(out["deltas"]) > 10


@pytest.mark.parametrize(
    "lname,rname,expect_identical",
    [
        ("Jane", "Jane", True),
        ("Jane", "jane ", True),
        ("Jane", "John", False),
    ],
)
def test_fingerprint_identity_on_names(lname, rname, expect_identical):
    left = {"passport": {"first_name": lname}, "attorney": {}}
    right = {"passport": {"first_name": rname}, "attorney": {}}
    fp_l = stable_fingerprint(left)
    fp_r = stable_fingerprint(right)
    assert (fp_l == fp_r) is expect_identical


def test_compare_extractions_filters_empty_deltas_by_default():
    out = compare_extractions({"passport": {}, "attorney": {}}, {"passport": {}, "attorney": {}})
    assert out["deltas"] == []


def test_builtin_presets_compare_cleanly():
    from app.extraction_compare_presets import PRESET_PAIRS

    for p in PRESET_PAIRS:
        out = compare_extractions_extended(
            p["left"],
            p["right"],
            label_left=str(p.get("label_left")),
            label_right=str(p.get("label_right")),
        )
        assert out["schema_version"] == 1
        assert "fingerprints" in out and "deltas" in out
