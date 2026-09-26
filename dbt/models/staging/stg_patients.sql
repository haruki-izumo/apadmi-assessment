select
    {{ trim_to_null('id') }} as patient_id,
    {{ trim_to_null('gender') }} as gender,
    cast(birth_date as date) as birth_date,
    cast(deceased_datetime as timestamptz) as deceased_datetime,
    {{ trim_to_null('city') }} as city,
    {{ trim_to_null('state') }} as state,
    {{ trim_to_null('postal_code') }} as postal_code,
    {{ trim_to_null('marital_status') }} as marital_status,
    {{ trim_to_null('race') }} as race,
    {{ trim_to_null('ethnicity') }} as ethnicity,
    {{ trim_to_null('source_file') }} as source_file,
    cast(ingested_at as timestamptz) as ingested_at
from read_parquet('../data/staging/patient.parquet')
