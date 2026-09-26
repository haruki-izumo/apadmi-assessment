-- Encounter.organization_id stores this identifier_value, not the FHIR resource id.
with organizations as (
    select
        md5(identifier_value) as organization_key,
        organization_id,
        identifier_value,
        name,
        city,
        state
    from {{ ref('stg_organizations') }}
)

select * from organizations

union all

select
    '-1' as organization_key,
    cast(null as varchar) as organization_id,
    cast(null as varchar) as identifier_value,
    'unknown' as name,
    cast(null as varchar) as city,
    cast(null as varchar) as state
