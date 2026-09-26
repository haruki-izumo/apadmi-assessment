-- Encounter.practitioner_id stores this identifier_value (NPI), not the FHIR resource id.
with practitioners as (
    select
        md5(identifier_value) as practitioner_key,
        practitioner_id,
        identifier_value,
        name,
        coalesce(gender, 'unknown') as gender
    from {{ ref('stg_practitioners') }}
)

select * from practitioners

union all

select
    '-1' as practitioner_key,
    cast(null as varchar) as practitioner_id,
    cast(null as varchar) as identifier_value,
    'unknown' as name,
    'unknown' as gender
