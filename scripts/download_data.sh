#!/usr/bin/env bash
# Download Synthea "100 Sample Synthetic Patient Records, FHIR R4" and unpack
# the JSON bundles into data/raw/fhir/.
#
# Primary URL is the "FHIR R4" link under "Latest Version of Synthea" on
# https://synthetichealth.github.io/downloads.html :
#   synthea_sample_data_fhir_latest.zip
# If that request fails, fall back to the earlier FHIR R4 archive on the same
# page (synthea_sample_data_fhir_r4_sep2019.zip).
#
# Idempotent: if data/raw/fhir/ already contains JSON files, exit without
# downloading again.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ROOT}/data/raw/fhir"

PRIMARY_URL="https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_fhir_latest.zip"
FALLBACK_URL="https://synthetichealth.github.io/synthea-sample-data/downloads/synthea_sample_data_fhir_r4_sep2019.zip"

mkdir -p "${DEST}"

shopt -s nullglob
existing=("${DEST}"/*.json)
shopt -u nullglob
if ((${#existing[@]} > 0)); then
  echo "Found ${#existing[@]} JSON file(s) in ${DEST}; skipping download."
  exit 0
fi

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "${tmpdir}"
}
trap cleanup EXIT

zip_path="${tmpdir}/synthea_fhir.zip"

download() {
  local url="$1"
  curl --fail --location --retry 3 --show-error --output "${zip_path}" "${url}"
}

echo "Downloading ${PRIMARY_URL}"
if ! download "${PRIMARY_URL}"; then
  echo "Primary URL failed; trying fallback ${FALLBACK_URL}"
  rm -f "${zip_path}"
  download "${FALLBACK_URL}"
fi

echo "Unpacking JSON bundles into ${DEST}"
unzip -q -o "${zip_path}" -d "${tmpdir}/unzipped"
find "${tmpdir}/unzipped" -type f -name '*.json' -exec mv {} "${DEST}/" \;

count="$(find "${DEST}" -maxdepth 1 -type f -name '*.json' | wc -l | tr -d ' ')"
echo "Done. ${count} JSON file(s) in ${DEST}."
