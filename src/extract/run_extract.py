"""Stream FHIR bundles into typed staging Parquet files.

One file is parsed at a time. Rows are kept until the end so we can
deduplicate on resource id, then each resource type is overwritten as
data/staging/<resource>.parquet.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import orjson
import pyarrow as pa
import pyarrow.parquet as pq

from src.extract.extractors import EXTRACTORS

logger = logging.getLogger("extract")

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw" / "fhir"
STAGING_DIR = REPO_ROOT / "data" / "staging"
REPORT_PATH = REPO_ROOT / "docs" / "extract_reconciliation.md"

STRING = pa.string()
TIMESTAMP = pa.timestamp("us", tz="UTC")
DATE = pa.date32()
FLOAT = pa.float64()

# Parquet names stay singular and lowercase: patient.parquet, encounter.parquet, ...
OUTPUT_NAMES = {
    "Patient": "patient",
    "Encounter": "encounter",
    "Condition": "condition",
    "Observation": "observation",
    "Organization": "organization",
    "Practitioner": "practitioner",
}

LINEAGE = [("source_file", STRING), ("ingested_at", TIMESTAMP)]

SCHEMAS: dict[str, pa.Schema] = {
    "Patient": pa.schema(
        [
            ("id", STRING),
            ("gender", STRING),
            ("birth_date", DATE),
            ("deceased_datetime", TIMESTAMP),
            ("city", STRING),
            ("state", STRING),
            ("postal_code", STRING),
            ("marital_status", STRING),
            ("race", STRING),
            ("ethnicity", STRING),
            *LINEAGE,
        ]
    ),
    "Encounter": pa.schema(
        [
            ("id", STRING),
            ("patient_id", STRING),
            ("class_code", STRING),
            ("type_system", STRING),
            ("type_code", STRING),
            ("type_display", STRING),
            ("start_ts", TIMESTAMP),
            ("end_ts", TIMESTAMP),
            ("organization_id", STRING),
            ("practitioner_id", STRING),
            ("reason_code", STRING),
            ("reason_display", STRING),
            *LINEAGE,
        ]
    ),
    "Condition": pa.schema(
        [
            ("id", STRING),
            ("patient_id", STRING),
            ("encounter_id", STRING),
            ("code_system", STRING),
            ("code", STRING),
            ("display", STRING),
            ("clinical_status", STRING),
            ("verification_status", STRING),
            ("onset_ts", TIMESTAMP),
            ("abatement_ts", TIMESTAMP),
            ("recorded_date", DATE),
            *LINEAGE,
        ]
    ),
    "Observation": pa.schema(
        [
            ("id", STRING),
            ("patient_id", STRING),
            ("encounter_id", STRING),
            ("category", STRING),
            ("code_system", STRING),
            ("code", STRING),
            ("display", STRING),
            ("effective_ts", TIMESTAMP),
            ("value_numeric", FLOAT),
            ("unit", STRING),
            ("value_text", STRING),
            ("parent_observation_id", STRING),
            *LINEAGE,
        ]
    ),
    "Organization": pa.schema(
        [
            ("id", STRING),
            ("identifier_value", STRING),
            ("name", STRING),
            ("city", STRING),
            ("state", STRING),
            *LINEAGE,
        ]
    ),
    "Practitioner": pa.schema(
        [
            ("id", STRING),
            ("identifier_value", STRING),
            ("name", STRING),
            ("gender", STRING),
            *LINEAGE,
        ]
    ),
}


def iter_bundle_files(raw_dir: Path) -> list[Path]:
    return sorted(
        path for path in raw_dir.iterdir() if path.is_file() and path.suffix.lower() == ".json"
    )


def write_parquet(resource_type: str, rows: list[dict[str, object]], staging_dir: Path) -> Path:
    """Overwrite staging/<resource>.parquet using the explicit Arrow schema."""
    schema = SCHEMAS[resource_type]
    table = pa.Table.from_pylist(rows, schema=schema)
    destination = staging_dir / f"{OUTPUT_NAMES[resource_type]}.parquet"
    pq.write_table(table, destination)
    return destination


def _as_rows(extracted: object) -> list[dict[str, object]]:
    if isinstance(extracted, list):
        return [row for row in extracted if isinstance(row, dict)]
    if isinstance(extracted, dict):
        return [extracted]
    return []


def build_report(
    *,
    files_processed: int,
    ingested_at: datetime,
    profile_counts: Counter[str],
    extracted_counts: Counter[str],
    skipped: Counter[tuple[str, str]],
) -> str:
    lines = [
        "# Extract reconciliation",
        "",
        f"- Files processed: {files_processed}",
        f"- Ingested at: {ingested_at.isoformat()}",
        "",
        "Profile count is the number of source resources of that type (the same",
        "definition as `docs/data_profile.md`, excluding the Bundle wrapper).",
        "Extracted rows are what landed in Parquet after id deduplication.",
        "Observation counts are expected to differ when panels such as blood",
        "pressure are expanded to one row per component.",
        "",
        "| resource | profile_count | extracted_rows | status |",
        "| --- | ---: | ---: | --- |",
    ]
    for resource_type in EXTRACTORS:
        profile_count = profile_counts[resource_type]
        extracted = extracted_counts[resource_type]
        if resource_type == "Observation":
            status = "ok (component explosion expected)"
        elif extracted == profile_count:
            status = "ok"
        else:
            status = "MISMATCH"
        lines.append(f"| {resource_type} | {profile_count:,} | {extracted:,} | {status} |")

    lines.extend(["", "## Skipped rows", ""])
    if not skipped:
        lines.append("None.")
    else:
        lines.extend(["| resource | reason | count |", "| --- | --- | ---: |"])
        for (resource_type, reason), count in sorted(skipped.items()):
            lines.append(f"| {resource_type} | {reason} | {count:,} |")
    lines.append("")
    return "\n".join(lines)


def log_reconciliation(
    profile_counts: Counter[str],
    extracted_counts: Counter[str],
    skipped: Counter[tuple[str, str]],
) -> None:
    for resource_type in EXTRACTORS:
        profile_count = profile_counts[resource_type]
        extracted = extracted_counts[resource_type]
        logger.info("%s rows: %s (profile %s)", resource_type, f"{extracted:,}", f"{profile_count:,}")
        if resource_type == "Observation":
            continue
        if extracted != profile_count:
            logger.warning(
                "%s mismatch: extracted %s rows vs profile count %s",
                resource_type,
                f"{extracted:,}",
                f"{profile_count:,}",
            )
    if not skipped:
        logger.info("rows skipped: none")
        return
    for (resource_type, reason), count in sorted(skipped.items()):
        logger.info("rows skipped %s %s: %s", resource_type, reason, f"{count:,}")


def run(raw_dir: Path = RAW_DIR, staging_dir: Path = STAGING_DIR, report_path: Path = REPORT_PATH) -> None:
    if not raw_dir.is_dir():
        raise SystemExit(f"Missing raw directory: {raw_dir}")

    files = iter_bundle_files(raw_dir)
    if not files:
        raise SystemExit(f"No JSON files in {raw_dir}")

    ingested_at = datetime.now(timezone.utc)
    seen: dict[str, set[str]] = {resource_type: set() for resource_type in EXTRACTORS}
    buckets: dict[str, list[dict[str, object]]] = {resource_type: [] for resource_type in EXTRACTORS}
    profile_counts: Counter[str] = Counter()
    skipped: Counter[tuple[str, str]] = Counter()
    files_processed = 0

    for path in files:
        try:
            document = orjson.loads(path.read_bytes())
        except orjson.JSONDecodeError as exc:
            logger.warning("skipped file %s: invalid JSON (%s)", path.name, exc)
            continue
        files_processed += 1
        entries = document.get("entry") if isinstance(document, dict) else None
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            resource = entry.get("resource")
            if not isinstance(resource, dict):
                continue
            resource_type = resource.get("resourceType")
            if not isinstance(resource_type, str):
                continue
            profile_counts[resource_type] += 1
            extractor = EXTRACTORS.get(resource_type)
            if extractor is None:
                continue

            resource_id = resource.get("id")
            if not isinstance(resource_id, str) or not resource_id.strip():
                skipped[(resource_type, "missing_id")] += 1
                continue
            if resource_id in seen[resource_type]:
                skipped[(resource_type, "duplicate_id")] += 1
                continue

            try:
                extracted = extractor(resource)
            except Exception as exc:
                skipped[(resource_type, "extract_error")] += 1
                logger.warning(
                    "rows skipped %s extract_error id=%s file=%s: %s",
                    resource_type,
                    resource_id,
                    path.name,
                    exc,
                )
                continue

            accepted: list[dict[str, object]] = []
            for row in _as_rows(extracted):
                if not isinstance(row.get("id"), str) or not row["id"]:
                    skipped[(resource_type, "missing_id")] += 1
                    continue
                row["source_file"] = path.name
                row["ingested_at"] = ingested_at
                accepted.append(row)
            if not accepted:
                skipped[(resource_type, "empty_extract")] += 1
                continue
            seen[resource_type].add(resource_id)
            buckets[resource_type].extend(accepted)

    staging_dir.mkdir(parents=True, exist_ok=True)
    extracted_counts: Counter[str] = Counter()
    for resource_type, rows in buckets.items():
        destination = write_parquet(resource_type, rows, staging_dir)
        extracted_counts[resource_type] = len(rows)
        logger.info("wrote %s (%s rows)", destination.name, f"{len(rows):,}")

    logger.info("files processed: %s", files_processed)
    log_reconciliation(profile_counts, extracted_counts, skipped)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_report(
            files_processed=files_processed,
            ingested_at=ingested_at,
            profile_counts=profile_counts,
            extracted_counts=extracted_counts,
            skipped=skipped,
        ),
        encoding="utf-8",
    )
    logger.info("wrote %s", report_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()
