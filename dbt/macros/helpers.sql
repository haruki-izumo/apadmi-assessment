{#-
  Shared expressions so staging, dimensions, and facts hash and date keys
  the same way. key '-1' (or date_key -1) is the unknown member.
-#}

{% macro trim_to_null(column_name) -%}
nullif(trim({{ column_name }}), '')
{%- endmacro %}


{% macro surrogate_key(fields) -%}
md5(concat(
    {%- for field in fields -%}
    coalesce(cast({{ field }} as varchar), '')
    {%- if not loop.last %}, '|', {% endif -%}
    {%- endfor -%}
))
{%- endmacro %}


{% macro key_or_unknown(fields) -%}
case
    when {% for field in fields %}{{ field }} is null{% if not loop.last %} and {% endif %}{% endfor %}
    then '-1'
    else {{ surrogate_key(fields) }}
end
{%- endmacro %}


{# Calendar date in UTC. A plain cast of timestamptz uses the session time zone. #}
{% macro utc_date(ts_expr) -%}
cast(({{ ts_expr }} at time zone 'UTC') as date)
{%- endmacro %}


{% macro date_key(date_expr) -%}
case
    when {{ date_expr }} is null then cast(-1 as integer)
    else cast(
        year({{ date_expr }}) * 10000
        + month({{ date_expr }}) * 100
        + day({{ date_expr }})
        as integer
    )
end
{%- endmacro %}


{# Completed whole years. A birthday later in the year does not count yet. #}
{% macro age_in_years(birth_date, event_date) -%}
case
    when {{ birth_date }} is null or {{ event_date }} is null then null
    else cast(
        datediff('year', {{ birth_date }}, {{ event_date }})
        - case
            when month({{ event_date }}) < month({{ birth_date }})
                or (
                    month({{ event_date }}) = month({{ birth_date }})
                    and day({{ event_date }}) < day({{ birth_date }})
                )
            then 1
            else 0
        end
        as integer
    )
end
{%- endmacro %}
