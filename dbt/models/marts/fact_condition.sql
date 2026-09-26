-- Grain: one row per recorded condition.
select
    md5(c.condition_id) as condition_key,
    c.condition_id,
    coalesce(p.patient_key, '-1') as patient_key,
    coalesce(e.encounter_key, '-1') as encounter_key,
    {{ key_or_unknown(['c.code_system', 'c.code', 'c.display']) }} as condition_code_key,
    {{ date_key(utc_date('c.onset_ts')) }} as onset_date_key,
    {{ date_key(utc_date('c.abatement_ts')) }} as abatement_date_key,
    coalesce(c.clinical_status = 'active', false) as is_active,
    case
        when c.onset_ts is null or c.abatement_ts is null then null
        else cast(datediff('day', {{ utc_date('c.onset_ts') }}, {{ utc_date('c.abatement_ts') }}) as integer)
    end as duration_days,
    {{ age_in_years('p.birth_date', utc_date('c.onset_ts')) }} as age_at_onset
from {{ ref('stg_conditions') }} as c
left join {{ ref('dim_patient') }} as p
    on c.patient_id = p.patient_id
left join {{ ref('fact_encounter') }} as e
    on c.encounter_id = e.encounter_id
