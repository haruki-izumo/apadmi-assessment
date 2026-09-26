"""Unit tests for path access, reference parsing, and observation components."""

from src.extract.extractors import extract_observation
from src.extract.fhir_utils import get, parse_ref


def test_get_walks_dicts_and_lists_and_returns_default_when_missing():
    patient = {"address": [{"city": "Boston"}], "active": False, "count": 0}

    assert get(patient, "address.0.city") == "Boston"
    assert get(patient, "active", default=True) is False
    assert get(patient, "count", default=5) == 0
    assert get(patient, "address.3.city", default="unknown") == "unknown"
    assert get(patient, "name.0.family", default=None) is None
    assert get(None, "address.0.city", default="missing") == "missing"
    assert get(patient, "address.city", default="missing") == "missing"


def test_parse_ref_urn_uuid_relative_and_conditional_identifier():
    assert parse_ref("urn:uuid:ee4b7339-ca58-b6af-c199-04b6d5761c73") == (
        "ee4b7339-ca58-b6af-c199-04b6d5761c73"
    )
    assert parse_ref("Patient/abc-123") == "abc-123"
    assert (
        parse_ref(
            "Organization?identifier=https://github.com/synthetichealth/synthea|4f59f709-8b84-3d27-a04b-c6b7b5544413"
        )
        == "4f59f709-8b84-3d27-a04b-c6b7b5544413"
    )
    assert (
        parse_ref("Practitioner?identifier=http://hl7.org/fhir/sid/us-npi|9999973297")
        == "9999973297"
    )
    assert parse_ref(None) is None
    assert parse_ref("") is None
    assert parse_ref("   ") is None


def test_extract_observation_emits_one_row_per_component():
    blood_pressure = {
        "resourceType": "Observation",
        "id": "obs-bp",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure"}]
        },
        "subject": {"reference": "urn:uuid:patient-1"},
        "encounter": {"reference": "Encounter/enc-1"},
        "effectiveDateTime": "2026-05-27T03:20:17+00:00",
        "component": [
            {
                "code": {
                    "coding": [
                        {"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic Blood Pressure"}
                    ]
                },
                "valueQuantity": {"value": 86, "unit": "mm[Hg]"},
            },
            {
                "code": {
                    "coding": [
                        {"system": "http://loinc.org", "code": "8480-6", "display": "Systolic Blood Pressure"}
                    ]
                },
                "valueQuantity": {"value": 109, "unit": "mm[Hg]"},
            },
        ],
    }

    rows = extract_observation(blood_pressure)

    assert len(rows) == 2
    assert [row["code"] for row in rows] == ["8462-4", "8480-6"]
    assert [row["id"] for row in rows] == ["obs-bp:8462-4", "obs-bp:8480-6"]
    assert {row["parent_observation_id"] for row in rows} == {"obs-bp"}
    assert [row["value_numeric"] for row in rows] == [86.0, 109.0]
    assert rows[0]["unit"] == "mm[Hg]"
    assert rows[0]["patient_id"] == "patient-1"
    assert rows[0]["encounter_id"] == "enc-1"
    assert rows[0]["category"] == "vital-signs"
    assert "85354-9" not in {row["code"] for row in rows}


def test_extract_observation_codeable_concept_lands_in_value_text():
    smoking = {
        "resourceType": "Observation",
        "id": "obs-smoke",
        "code": {"coding": [{"system": "http://loinc.org", "code": "72166-2", "display": "Tobacco smoking status"}]},
        "subject": {"reference": "Patient/patient-1"},
        "valueCodeableConcept": {
            "coding": [{"system": "http://snomed.info/sct", "code": "266919005", "display": "Never smoked tobacco"}],
            "text": "Never smoked tobacco",
        },
    }

    rows = extract_observation(smoking)

    assert len(rows) == 1
    assert rows[0]["parent_observation_id"] is None
    assert rows[0]["value_numeric"] is None
    assert rows[0]["value_text"] == "Never smoked tobacco"
    assert rows[0]["code"] == "72166-2"
