with types as (
    select distinct
        {{ key_or_unknown(['class_code', 'type_code', 'type_display']) }} as encounter_type_key,
        class_code,
        type_code,
        type_display
    from {{ ref('stg_encounters') }}
    where class_code is not null
        or type_code is not null
        or type_display is not null
)

select * from types

union all

select
    '-1' as encounter_type_key,
    cast(null as varchar) as class_code,
    cast(null as varchar) as type_code,
    'unknown' as type_display
