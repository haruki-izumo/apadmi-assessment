with codes as (
    select distinct
        {{ key_or_unknown(['code_system', 'code', 'display', 'category', 'unit']) }} as observation_code_key,
        code_system,
        code as loinc_code,
        display,
        category,
        unit
    from {{ ref('stg_observations') }}
    where code_system is not null
        or code is not null
        or display is not null
        or category is not null
        or unit is not null
)

select * from codes

union all

select
    '-1' as observation_code_key,
    cast(null as varchar) as code_system,
    cast(null as varchar) as loinc_code,
    'unknown' as display,
    cast(null as varchar) as category,
    cast(null as varchar) as unit
