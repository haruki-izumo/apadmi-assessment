-- Continuous calendar from the earliest to the latest clinical event date,
-- plus one unknown row (date_key -1) for missing fact dates.
with event_dates as (
    select {{ utc_date('start_ts') }} as event_date from {{ ref('stg_encounters') }}
    union all
    select {{ utc_date('end_ts') }} from {{ ref('stg_encounters') }}
    union all
    select {{ utc_date('onset_ts') }} from {{ ref('stg_conditions') }}
    union all
    select {{ utc_date('abatement_ts') }} from {{ ref('stg_conditions') }}
    union all
    select {{ utc_date('effective_ts') }} from {{ ref('stg_observations') }}
),

bounds as (
    select
        min(event_date) as min_date,
        max(event_date) as max_date
    from event_dates
    where event_date is not null
),

spine as (
    select cast(generate_series as date) as date_day
    from bounds
    cross join generate_series(bounds.min_date, bounds.max_date, interval 1 day)
)

select
    {{ date_key('date_day') }} as date_key,
    date_day as "date",
    cast(year(date_day) as integer) as year,
    cast(quarter(date_day) as integer) as quarter,
    cast(month(date_day) as integer) as month,
    monthname(date_day) as month_name,
    dayname(date_day) as day_of_week,
    isodow(date_day) in (6, 7) as is_weekend
from spine

union all

select
    cast(-1 as integer) as date_key,
    cast(null as date) as "date",
    cast(null as integer) as year,
    cast(null as integer) as quarter,
    cast(null as integer) as month,
    'unknown' as month_name,
    'unknown' as day_of_week,
    cast(null as boolean) as is_weekend
