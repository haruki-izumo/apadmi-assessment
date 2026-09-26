-- One row per patient. Age is not stored; facts calculate it at the event date.
with patients as (
    select
        md5(patient_id) as patient_key,
        patient_id,
        coalesce(gender, 'unknown') as gender,
        birth_date,
        deceased_datetime is not null as is_deceased,
        {{ utc_date('deceased_datetime') }} as deceased_date,
        city,
        state,
        marital_status,
        race,
        ethnicity
    from {{ ref('stg_patients') }}
)

select * from patients

union all

select
    '-1' as patient_key,
    cast(null as varchar) as patient_id,
    'unknown' as gender,
    cast(null as date) as birth_date,
    cast(null as boolean) as is_deceased,
    cast(null as date) as deceased_date,
    'unknown' as city,
    'unknown' as state,
    'unknown' as marital_status,
    'unknown' as race,
    'unknown' as ethnicity
