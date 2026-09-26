-- BMI by gender and age bracket.
--
-- Paediatric BMI is normally assessed by percentile, so the 0-17 bracket is
-- indicative only. This model uses the BMI ratio (LOINC 39156-5, kg/m2), not
-- the BMI-for-age percentile.
--
-- Each patient's readings are averaged inside a bracket first. Those patient
-- means are then averaged, so a patient with many readings is not overweighted.

with readings as (
    select
        p.gender,
        f.patient_key,
        f.value_numeric as bmi,
        case
            when f.age_at_observation between 0 and 17 then '0-17'
            when f.age_at_observation between 18 and 34 then '18-34'
            when f.age_at_observation between 35 and 49 then '35-49'
            when f.age_at_observation between 50 and 64 then '50-64'
            when f.age_at_observation >= 65 then '65+'
        end as age_bracket
    from {{ ref('fact_observation') }} as f
    inner join {{ ref('dim_observation_code') }} as c
        on f.observation_code_key = c.observation_code_key
    inner join {{ ref('dim_patient') }} as p
        on f.patient_key = p.patient_key
    where c.loinc_code = '39156-5'
        and f.value_numeric is not null
        and f.age_at_observation is not null
        and p.patient_key <> '-1'
),

patient_means as (
    select
        gender,
        age_bracket,
        patient_key,
        avg(bmi) as patient_avg_bmi,
        count(*) as reading_count
    from readings
    where age_bracket is not null
    group by gender, age_bracket, patient_key
)

select
    gender,
    age_bracket,
    round(avg(patient_avg_bmi), 1) as avg_bmi,
    count(*) as patient_count,
    sum(reading_count) as reading_count
from patient_means
group by gender, age_bracket
order by
    case age_bracket
        when '0-17' then 1
        when '18-34' then 2
        when '35-49' then 3
        when '50-64' then 4
        when '65+' then 5
    end,
    gender
