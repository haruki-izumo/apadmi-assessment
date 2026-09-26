-- BMI ratio (LOINC 39156-5, kg/m2) must sit between 10 and 80.
-- BMI percentile (LOINC 59576-9) is a different measure and is not tested here.
select
    f.observation_key,
    f.value_numeric
from {{ ref('fact_observation') }} as f
inner join {{ ref('dim_observation_code') }} as c
    on f.observation_code_key = c.observation_code_key
where c.loinc_code = '39156-5'
    and f.value_numeric is not null
    and (f.value_numeric < 10 or f.value_numeric > 80)
