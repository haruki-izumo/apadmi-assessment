"""Profile every JSON file in data/raw/fhir/ and write docs/data_profile.md.

Each file is a FHIR R4 Bundle: one patient record, or a hospitalInformation /
practitionerInformation bundle. Counts include the bundle document itself and
every resource in Bundle.entry.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import orjson

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw" / "fhir"
OUTPUT_PATH = REPO_ROOT / "docs" / "data_profile.md"


def resource_types(document: object) -> list[str]:
    """Return resourceType values for a bundle document and its entries."""
    if not isinstance(document, dict):
        return []

    found: list[str] = []
    top_level = document.get("resourceType")
    if isinstance(top_level, str):
        found.append(top_level)

    entries = document.get("entry")
    if not isinstance(entries, list):
        return found

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            continue
        resource_type = resource.get("resourceType")
        if isinstance(resource_type, str):
            found.append(resource_type)
    return found


def format_bytes(size: int) -> str:
    """Format a byte count as B, KB, or MB."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def build_report(files: list[Path]) -> str:
    """Summarise file sizes and resourceType counts."""
    counts: Counter[str] = Counter()
    total_size = 0
    largest = files[0]
    largest_size = files[0].stat().st_size

    for path in files:
        size = path.stat().st_size
        total_size += size
        if size > largest_size:
            largest = path
            largest_size = size
        document = orjson.loads(path.read_bytes())
        counts.update(resource_types(document))

    rows = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    lines = [
        "# FHIR data profile",
        "",
        f"- Files: {len(files)}",
        f"- Total size: {format_bytes(total_size)} ({total_size:,} bytes)",
        f"- Largest file: `{largest.name}` ({format_bytes(largest_size)})",
        "",
        "| resourceType | count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {resource_type} | {count:,} |" for resource_type, count in rows)
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if not RAW_DIR.is_dir():
        raise SystemExit(f"Missing raw directory: {RAW_DIR}")

    files = sorted(
        path
        for path in RAW_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".json"
    )
    if not files:
        raise SystemExit(f"No JSON files in {RAW_DIR}. Run scripts/download_data.sh first.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_report(files), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(files)} files)")


if __name__ == "__main__":
    main()
