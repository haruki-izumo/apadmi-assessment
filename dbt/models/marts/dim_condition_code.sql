with codes as (
    select distinct
        {{ key_or_unknown(['code_system', 'code', 'display']) }} as condition_code_key,
        code_system,
        code,
        display
    from {{ ref('stg_conditions') }}
    where code_system is not null
        or code is not null
        or display is not null
)

select * from codes

union all

select
    '-1' as condition_code_key,
    cast(null as varchar) as code_system,
    cast(null as varchar) as code,
    'unknown' as display
