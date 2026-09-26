"""Small helpers for reading FHIR JSON without raising on missing data."""

from __future__ import annotations

from datetime import date, datetime, timezone


def get(obj: object, path: str, default: object = None) -> object:
    """Walk a dotted path. Numeric segments index lists. Missing data returns default.

    Example: get(patient, "address.0.city") -> "Boston"
    """
    current = obj
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return default
            current = current[part]
            continue
        if isinstance(current, list):
            if not part.isdigit():
                return default
            index = int(part)
            if index >= len(current):
                return default
            current = current[index]
            continue
        return default
    return current


def parse_ref(ref: str | None) -> str | None:
    """Return the id inside a FHIR reference, or None when it is missing.

    Handles the three forms Synthea uses:
    - urn:uuid:<id>
    - Patient/<id> (any ResourceType/<id>)
    - Organization?identifier=https://example.org|<id>
    """
    if ref is None:
        return None
    text = ref.strip()
    if not text:
        return None

    if "identifier=" in text:
        _, _, identifier = text.partition("identifier=")
        if "|" not in identifier:
            return None
        value = identifier.split("|", 1)[1].split("&", 1)[0].strip()
        return value or None

    if text.startswith("urn:uuid:"):
        value = text.removeprefix("urn:uuid:").strip()
        return value or None

    if "://" not in text and "/" in text:
        _, _, remainder = text.partition("/")
        value = remainder.split("/", 1)[0].strip()
        return value or None

    return None


def parse_ts(value: object) -> datetime | None:
    """Parse a FHIR dateTime into a timezone-aware UTC datetime. Never raises."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_date(value: object) -> date | None:
    """Parse a FHIR date (or dateTime) into a date. Never raises."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def first_coding(codeable_concept: object) -> tuple[str | None, str | None, str | None]:
    """Return (system, code, display) from the first coding, or Nones."""
    coding = get(codeable_concept, "coding.0")
    if not isinstance(coding, dict):
        return (None, None, None)

    def _text(key: str) -> str | None:
        raw = coding.get(key)
        if isinstance(raw, str) and raw:
            return raw
        return None

    return (_text("system"), _text("code"), _text("display"))
