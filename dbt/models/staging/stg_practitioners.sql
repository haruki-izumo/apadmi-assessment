select
    {{ trim_to_null('id') }} as practitioner_id,
    {{ trim_to_null('identifier_value') }} as identifier_value,
    {{ trim_to_null('name') }} as name,
    {{ trim_to_null('gender') }} as gender,
    {{ trim_to_null('source_file') }} as source_file,
    cast(ingested_at as timestamptz) as ingested_at
from read_parquet('../data/staging/practitioner.parquet')
