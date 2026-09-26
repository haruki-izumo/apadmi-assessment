"""Pure extractors: one FHIR resource in, one flat row (or rows) out.

Lineage columns (source_file, ingested_at) are added by run_extract so these
functions stay easy to test with a resource dict alone.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from src.extract.fhir_utils import first_coding, get, parse_date, parse_ref, parse_ts

Row = dict[str, object]
Extractor = Callable[[dict], Row | list[Row]]

US_CORE_RACE = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
US_CORE_ETHNICITY = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity"
SYNTHEA_IDENTIFIER = "https://github.com/synthetichealth/synthea"
NPI_IDENTIFIER = "http://hl7.org/fhir/sid/us-npi"


def _text(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _coding_fields(concept: object) -> tuple[str | None, str | None, str | None]:
    """First coding, falling back to CodeableConcept.text for display."""
    system, code, display = first_coding(concept)
    if display is None:
        display = _text(get(concept, "text"))
    return system, code, display


def _code(concept: object) -> str | None:
    _, code, _ = first_coding(concept)
    return code


def _identifier_value(resource: dict, system: str | None = None) -> str | None:
    identifiers = resource.get("identifier")
    if not isinstance(identifiers, list):
        return None
    fallback: str | None = None
    for identifier in identifiers:
        if not isinstance(identifier, dict):
            continue
        value = _text(identifier.get("value"))
        if value is None:
            continue
        if system is not None and identifier.get("system") == system:
            return value
        if fallback is None:
            fallback = value
    return fallback


def _omb_display(resource: dict, extension_url: str) -> str | None:
    """US Core race/ethnicity: display on the ombCategory sub-extension."""
    extensions = resource.get("extension")
    if not isinstance(extensions, list):
        return None
    for extension in extensions:
        if not isinstance(extension, dict) or extension.get("url") != extension_url:
            continue
        nested = extension.get("extension")
        if not isinstance(nested, list):
            return None
        for item in nested:
            if isinstance(item, dict) and item.get("url") == "ombCategory":
                return _text(get(item, "valueCoding.display"))
        return None
    return None


def _human_name(resource: dict) -> str | None:
    names = resource.get("name")
    if not isinstance(names, list) or not names or not isinstance(names[0], dict):
        return None
    name = names[0]
    parts: list[str] = []
    for key in ("prefix", "given"):
        values = name.get(key)
        if isinstance(values, list):
            parts.extend(item for item in values if isinstance(item, str) and item)
    family = _text(name.get("family"))
    if family:
        parts.append(family)
    return " ".join(parts) or None


def _value_parts(node: dict) -> tuple[float | None, str | None, str | None]:
    """Return (value_numeric, unit, value_text) from a value[x] element."""
    quantity = node.get("valueQuantity")
    if isinstance(quantity, dict):
        raw = quantity.get("value")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return float(raw), _text(quantity.get("unit")), None

    concept = node.get("valueCodeableConcept")
    if isinstance(concept, dict):
        _, _, display = _coding_fields(concept)
        return None, None, display

    text = _text(node.get("valueString"))
    if text is not None:
        return None, None, text
    return None, None, None


def _effective_ts(resource: dict) -> datetime | None:
    if isinstance(resource.get("effectiveDateTime"), str):
        return parse_ts(resource["effectiveDateTime"])
    start = get(resource, "effectivePeriod.start")
    return parse_ts(start) if isinstance(start, str) else None


def _practitioner_id(resource: dict) -> str | None:
    """Prefer the primary performer (PPRF); otherwise the first participant."""
    participants = resource.get("participant")
    if not isinstance(participants, list):
        return None
    fallback: str | None = None
    for participant in participants:
        if not isinstance(participant, dict):
            continue
        ref = get(participant, "individual.reference")
        parsed = parse_ref(ref if isinstance(ref, str) else None)
        if parsed is None:
            continue
        if fallback is None:
            fallback = parsed
        if get(participant, "type.0.coding.0.code") == "PPRF":
            return parsed
    return fallback


def extract_patient(resource: dict) -> Row:
    _, marital_code, marital_display = _coding_fields(resource.get("maritalStatus"))
    deceased = resource.get("deceasedDateTime")
    return {
        "id": _text(resource.get("id")),
        "gender": _text(resource.get("gender")),
        "birth_date": parse_date(resource.get("birthDate")),
        "deceased_datetime": parse_ts(deceased) if isinstance(deceased, str) else None,
        "city": _text(get(resource, "address.0.city")),
        "state": _text(get(resource, "address.0.state")),
        "postal_code": _text(get(resource, "address.0.postalCode")),
        "marital_status": marital_display or marital_code,
        "race": _omb_display(resource, US_CORE_RACE),
        "ethnicity": _omb_display(resource, US_CORE_ETHNICITY),
    }


def extract_encounter(resource: dict) -> Row:
    type_system, type_code, type_display = _coding_fields(get(resource, "type.0"))
    reason_system, reason_code, reason_display = _coding_fields(get(resource, "reasonCode.0"))
    del reason_system
    subject = get(resource, "subject.reference")
    provider = get(resource, "serviceProvider.reference")
    return {
        "id": _text(resource.get("id")),
        "patient_id": parse_ref(subject if isinstance(subject, str) else None),
        "class_code": _text(get(resource, "class.code")),
        "type_system": type_system,
        "type_code": type_code,
        "type_display": type_display,
        "start_ts": parse_ts(get(resource, "period.start")),
        "end_ts": parse_ts(get(resource, "period.end")),
        "organization_id": parse_ref(provider if isinstance(provider, str) else None),
        "practitioner_id": _practitioner_id(resource),
        "reason_code": reason_code,
        "reason_display": reason_display,
    }


def extract_condition(resource: dict) -> Row:
    code_system, code, display = _coding_fields(resource.get("code"))
    subject = get(resource, "subject.reference")
    encounter = get(resource, "encounter.reference")
    onset = resource.get("onsetDateTime")
    abatement = resource.get("abatementDateTime")
    return {
        "id": _text(resource.get("id")),
        "patient_id": parse_ref(subject if isinstance(subject, str) else None),
        "encounter_id": parse_ref(encounter if isinstance(encounter, str) else None),
        "code_system": code_system,
        "code": code,
        "display": display,
        "clinical_status": _code(resource.get("clinicalStatus")),
        "verification_status": _code(resource.get("verificationStatus")),
        "onset_ts": parse_ts(onset) if isinstance(onset, str) else None,
        "abatement_ts": parse_ts(abatement) if isinstance(abatement, str) else None,
        "recorded_date": parse_date(resource.get("recordedDate")),
    }


def _observation_row(
    resource: dict,
    *,
    row_id: str | None,
    concept: object,
    value_node: dict,
    parent_observation_id: str | None,
) -> Row:
    code_system, code, display = _coding_fields(concept)
    value_numeric, unit, value_text = _value_parts(value_node)
    subject = get(resource, "subject.reference")
    encounter = get(resource, "encounter.reference")
    return {
        "id": row_id,
        "patient_id": parse_ref(subject if isinstance(subject, str) else None),
        "encounter_id": parse_ref(encounter if isinstance(encounter, str) else None),
        "category": _code(get(resource, "category.0")),
        "code_system": code_system,
        "code": code,
        "display": display,
        "effective_ts": _effective_ts(resource),
        "value_numeric": value_numeric,
        "unit": unit,
        "value_text": value_text,
        "parent_observation_id": parent_observation_id,
    }


def extract_observation(resource: dict) -> list[Row]:
    """One row, or one row per component when component[] is present.

    Component rows use "{observation_id}:{component_code}" as their own id.
    parent_observation_id points back at the panel. Repeated component codes
    in one observation get an index suffix so the row ids stay unique.
    """
    parent_id = _text(resource.get("id"))
    components = resource.get("component")
    if isinstance(components, list) and components:
        rows: list[Row] = []
        used_ids: set[str] = set()
        for index, component in enumerate(components):
            if not isinstance(component, dict):
                continue
            _, code, _ = _coding_fields(component.get("code"))
            suffix = code if code else str(index)
            row_id = f"{parent_id}:{suffix}" if parent_id else None
            if row_id is not None and row_id in used_ids:
                row_id = f"{row_id}:{index}"
            if row_id is not None:
                used_ids.add(row_id)
            rows.append(
                _observation_row(
                    resource,
                    row_id=row_id,
                    concept=component.get("code"),
                    value_node=component,
                    parent_observation_id=parent_id,
                )
            )
        return rows

    return [
        _observation_row(
            resource,
            row_id=parent_id,
            concept=resource.get("code"),
            value_node=resource,
            parent_observation_id=None,
        )
    ]


def extract_organization(resource: dict) -> Row:
    return {
        "id": _text(resource.get("id")),
        "identifier_value": _identifier_value(resource, SYNTHEA_IDENTIFIER),
        "name": _text(resource.get("name")),
        "city": _text(get(resource, "address.0.city")),
        "state": _text(get(resource, "address.0.state")),
    }


def extract_practitioner(resource: dict) -> Row:
    return {
        "id": _text(resource.get("id")),
        "identifier_value": _identifier_value(resource, NPI_IDENTIFIER),
        "name": _human_name(resource),
        "gender": _text(resource.get("gender")),
    }


EXTRACTORS: dict[str, Extractor] = {
    "Patient": extract_patient,
    "Encounter": extract_encounter,
    "Condition": extract_condition,
    "Observation": extract_observation,
    "Organization": extract_organization,
    "Practitioner": extract_practitioner,
}
