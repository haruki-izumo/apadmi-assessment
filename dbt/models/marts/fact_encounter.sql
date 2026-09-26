-- Grain: one row per encounter.
select
    md5(e.encounter_id) as encounter_key,
    e.encounter_id,
    coalesce(p.patient_key, '-1') as patient_key,
    {{ date_key(utc_date('e.start_ts')) }} as start_date_key,
    {{ date_key(utc_date('e.end_ts')) }} as end_date_key,
    {{ key_or_unknown(['e.class_code', 'e.type_code', 'e.type_display']) }} as encounter_type_key,
    coalesce(o.organization_key, '-1') as organization_key,
    coalesce(pr.practitioner_key, '-1') as practitioner_key,
    cast(datediff('minute', e.start_ts, e.end_ts) as integer) as duration_minutes,
    e.class_code = 'EMER' as is_emergency,
    e.class_code = 'IMP' as is_inpatient,
    {{ age_in_years('p.birth_date', utc_date('e.start_ts')) }} as age_at_encounter
from {{ ref('stg_encounters') }} as e
left join {{ ref('dim_patient') }} as p
    on e.patient_id = p.patient_id
left join {{ ref('dim_organization') }} as o
    on e.organization_id = o.identifier_value
left join {{ ref('dim_practitioner') }} as pr
    on e.practitioner_id = pr.identifier_value
