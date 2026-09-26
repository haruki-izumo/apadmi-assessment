-- Grain: one row per observation value. Component panels are already one row per component.
select
    md5(o.observation_id) as observation_key,
    coalesce(p.patient_key, '-1') as patient_key,
    coalesce(e.encounter_key, '-1') as encounter_key,
    {{ key_or_unknown(['o.code_system', 'o.code', 'o.display', 'o.category', 'o.unit']) }} as observation_code_key,
    {{ date_key(utc_date('o.effective_ts')) }} as date_key,
    o.value_numeric,
    o.value_text,
    o.unit,
    {{ age_in_years('p.birth_date', utc_date('o.effective_ts')) }} as age_at_observation
from {{ ref('stg_observations') }} as o
left join {{ ref('dim_patient') }} as p
    on o.patient_id = p.patient_id
left join {{ ref('fact_encounter') }} as e
    on o.encounter_id = e.encounter_id
