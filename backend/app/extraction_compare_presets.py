"""
Curated merged extraction pairs for demos, QA fixtures, and regression snapshots.

Not imported by default request paths; safe to use from notebooks or tests.
"""

from __future__ import annotations

from typing import Any

PresetPair = dict[str, Any]

PRESET_PAIRS: list[PresetPair] = [
    {
        "id": "name_typo",
        "label_left": "model_a",
        "label_right": "model_b",
        "left": {
            "passport": {
                "last_name": "Martinez",
                "first_name": "Elena",
                "passport_number": "P9012345",
                "date_of_birth": "1992-06-11",
                "date_of_expiration": "2032-06-11",
            },
            "attorney": {
                "family_name": "Cho",
                "given_name": "Daniel",
                "email": "dcho@firm.example",
                "city": "Portland",
                "state": "OR",
                "zip_code": "97205",
            },
        },
        "right": {
            "passport": {
                "last_name": "Martinez",
                "first_name": "Elana",
                "passport_number": "P9012345",
                "date_of_birth": "1992-06-11",
                "date_of_expiration": "2032-06-11",
            },
            "attorney": {
                "family_name": "Cho",
                "given_name": "Daniel",
                "email": "dcho@firm.example",
                "city": "Portland",
                "state": "OR",
                "zip_code": "97205",
            },
        },
    },
    {
        "id": "attorney_contact_drift",
        "label_left": "morning_run",
        "label_right": "afternoon_run",
        "left": {
            "passport": {
                "last_name": "Patel",
                "first_name": "Ravi",
                "passport_number": "N1122334",
                "nationality": "Canadian",
                "date_of_birth": "1988-01-22",
                "date_of_expiration": "2029-01-22",
            },
            "attorney": {
                "family_name": "Ibrahim",
                "given_name": "Sana",
                "email": "sana.ibrahim@law.example",
                "daytime_telephone": "+1 (503) 555-0142",
                "mobile_telephone": "+1 (503) 555-0199",
                "city": "Seattle",
                "state": "WA",
                "zip_code": "98101",
            },
        },
        "right": {
            "passport": {
                "last_name": "Patel",
                "first_name": "Ravi",
                "passport_number": "N1122334",
                "nationality": "Canadian",
                "date_of_birth": "1988-01-22",
                "date_of_expiration": "2029-01-22",
            },
            "attorney": {
                "family_name": "Ibrahim",
                "given_name": "Sana",
                "email": "sana@law.example",
                "daytime_telephone": "+1 (503) 555-0142",
                "mobile_telephone": "+1 (503) 555-0142",
                "city": "Seattle",
                "state": "WA",
                "zip_code": "98101",
            },
        },
    },
    {
        "id": "passport_only_vs_full",
        "label_left": "passport_only",
        "label_right": "passport_plus_g28",
        "left": {
            "passport": {
                "last_name": "Okafor",
                "first_name": "Chidi",
                "middle_name": "K.",
                "passport_number": "A9876543",
                "country_of_issue": "Nigeria",
                "nationality": "Nigerian",
                "date_of_birth": "1995-09-30",
                "place_of_birth": "Lagos",
                "sex": "M",
                "date_of_issue": "2018-09-30",
                "date_of_expiration": "2028-09-30",
            },
            "attorney": {},
        },
        "right": {
            "passport": {
                "last_name": "Okafor",
                "first_name": "Chidi",
                "middle_name": "K.",
                "passport_number": "A9876543",
                "country_of_issue": "Nigeria",
                "nationality": "Nigerian",
                "date_of_birth": "1995-09-30",
                "place_of_birth": "Lagos",
                "sex": "M",
                "date_of_issue": "2018-09-30",
                "date_of_expiration": "2028-09-30",
            },
            "attorney": {
                "family_name": "Reyes",
                "given_name": "Maria",
                "email": "mreyes@counsel.example",
                "bar_number": "WA123456",
                "licensing_authority": "Washington State Bar",
                "street_number_and_name": "1900 First Avenue",
                "city": "Seattle",
                "state": "WA",
                "zip_code": "98101",
                "country": "USA",
            },
        },
    },
    {
        "id": "expiry_correction",
        "label_left": "ocr_v1",
        "label_right": "human_fix",
        "left": {
            "passport": {
                "last_name": "Hernandez",
                "first_name": "Luis",
                "passport_number": "X4455667",
                "date_of_birth": "1991-03-15",
                "date_of_expiration": "2020-03-15",
            },
            "attorney": {
                "family_name": "Nguyen",
                "given_name": "Amy",
                "email": "amy@immigration.example",
            },
        },
        "right": {
            "passport": {
                "last_name": "Hernandez",
                "first_name": "Luis",
                "passport_number": "X4455667",
                "date_of_birth": "1991-03-15",
                "date_of_expiration": "2030-03-15",
            },
            "attorney": {
                "family_name": "Nguyen",
                "given_name": "Amy",
                "email": "amy@immigration.example",
            },
        },
    },
    {
        "id": "unmapped_custom_keys",
        "label_left": "intake_raw",
        "label_right": "intake_cleaned",
        "left": {
            "passport": {
                "last_name": "Smith",
                "first_name": "Taylor",
                "passport_number": "R3344556",
                "reviewer_flag": "needs_secondary_id",
            },
            "attorney": {
                "family_name": "Brown",
                "given_name": "Jordan",
                "email": "jordan@firm.example",
                "internal_matter_id": "M-102938",
            },
        },
        "right": {
            "passport": {
                "last_name": "Smith",
                "first_name": "Taylor",
                "passport_number": "R3344556",
            },
            "attorney": {
                "family_name": "Brown",
                "given_name": "Jordan",
                "email": "jordan@firm.example",
            },
        },
    },
]


def get_preset(pair_id: str) -> PresetPair | None:
    for p in PRESET_PAIRS:
        if p.get("id") == pair_id:
            return p
    return None


def list_preset_ids() -> list[str]:
    return [str(p["id"]) for p in PRESET_PAIRS if p.get("id")]
