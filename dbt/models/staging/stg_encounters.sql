select
    {{ trim_to_null('id') }} as encounter_id,
    {{ trim_to_null('patient_id') }} as patient_id,
    {{ trim_to_null('class_code') }} as class_code,
    {{ trim_to_null('type_system') }} as type_system,
    {{ trim_to_null('type_code') }} as type_code,
    {{ trim_to_null('type_display') }} as type_display,
    cast(start_ts as timestamptz) as start_ts,
    cast(end_ts as timestamptz) as end_ts,
    {{ trim_to_null('organization_id') }} as organization_id,
    {{ trim_to_null('practitioner_id') }} as practitioner_id,
    {{ trim_to_null('reason_code') }} as reason_code,
    {{ trim_to_null('reason_display') }} as reason_display,
    {{ trim_to_null('source_file') }} as source_file,
    cast(ingested_at as timestamptz) as ingested_at
from read_parquet('../data/staging/encounter.parquet')
