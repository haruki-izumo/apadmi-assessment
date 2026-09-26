select
    {{ trim_to_null('id') }} as observation_id,
    {{ trim_to_null('patient_id') }} as patient_id,
    {{ trim_to_null('encounter_id') }} as encounter_id,
    {{ trim_to_null('category') }} as category,
    {{ trim_to_null('code_system') }} as code_system,
    {{ trim_to_null('code') }} as code,
    {{ trim_to_null('display') }} as display,
    cast(effective_ts as timestamptz) as effective_ts,
    cast(value_numeric as double) as value_numeric,
    {{ trim_to_null('unit') }} as unit,
    {{ trim_to_null('value_text') }} as value_text,
    {{ trim_to_null('parent_observation_id') }} as parent_observation_id,
    {{ trim_to_null('source_file') }} as source_file,
    cast(ingested_at as timestamptz) as ingested_at
from read_parquet('../data/staging/observation.parquet')
