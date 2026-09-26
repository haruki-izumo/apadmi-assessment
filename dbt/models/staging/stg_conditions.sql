select
    {{ trim_to_null('id') }} as condition_id,
    {{ trim_to_null('patient_id') }} as patient_id,
    {{ trim_to_null('encounter_id') }} as encounter_id,
    {{ trim_to_null('code_system') }} as code_system,
    {{ trim_to_null('code') }} as code,
    {{ trim_to_null('display') }} as display,
    {{ trim_to_null('clinical_status') }} as clinical_status,
    {{ trim_to_null('verification_status') }} as verification_status,
    cast(onset_ts as timestamptz) as onset_ts,
    cast(abatement_ts as timestamptz) as abatement_ts,
    cast(recorded_date as date) as recorded_date,
    {{ trim_to_null('source_file') }} as source_file,
    cast(ingested_at as timestamptz) as ingested_at
from read_parquet('../data/staging/condition.parquet')
