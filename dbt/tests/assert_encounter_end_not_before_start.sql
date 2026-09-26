-- Fail when an encounter ends before it starts.
select
    encounter_id,
    start_ts,
    end_ts
from {{ ref('stg_encounters') }}
where end_ts < start_ts
