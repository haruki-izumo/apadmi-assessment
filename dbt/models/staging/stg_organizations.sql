select
    {{ trim_to_null('id') }} as organization_id,
    {{ trim_to_null('identifier_value') }} as identifier_value,
    {{ trim_to_null('name') }} as name,
    {{ trim_to_null('city') }} as city,
    {{ trim_to_null('state') }} as state,
    {{ trim_to_null('source_file') }} as source_file,
    cast(ingested_at as timestamptz) as ingested_at
from read_parquet('../data/staging/organization.parquet')
