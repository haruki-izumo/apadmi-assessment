"""Clinical overview of the FHIR DuckDB warehouse.

Run from the repository root:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "fhir.duckdb"
AGE_BRACKETS = ["0-17", "18-34", "35-49", "50-64", "65+"]
CLASS_ORDER = ["AMB", "EMER", "HH", "IMP", "VR"]

# Paediatric BMI is normally assessed by percentile, so the 0-17 bracket is indicative only.
BMI_NOTE = (
    "Paediatric BMI is normally assessed by percentile, so the 0-17 bracket is indicative only. "
    "Averages use LOINC 39156-5 (kg/m2). Each patient is averaged within a bracket before "
    "patients are averaged together."
)


def query(sql: str, params: list[object]) -> pd.DataFrame:
    """Run one read-only query. The warehouse is not modified."""
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        return connection.execute(sql, params).df()


def _gender_clause() -> str:
    return "(? = 'All' or p.gender = ?)"


@st.cache_data
def load_year_bounds() -> tuple[int, int]:
    frame = query(
        "select min(year) as min_year, max(year) as max_year from dim_date where year is not null",
        [],
    )
    return int(frame.loc[0, "min_year"]), int(frame.loc[0, "max_year"])


@st.cache_data
def load_genders() -> list[str]:
    frame = query(
        """
        select distinct gender
        from dim_patient
        where patient_key <> '-1'
          and gender is not null
        order by gender
        """,
        [],
    )
    return frame["gender"].tolist()


@st.cache_data
def load_kpis(gender: str, year_start: int, year_end: int) -> dict[str, int]:
    frame = query(
        f"""
        with encounters as (
            select e.patient_key
            from fact_encounter as e
            inner join dim_patient as p on e.patient_key = p.patient_key
            inner join dim_date as d on e.start_date_key = d.date_key
            where d.year between ? and ?
              and {_gender_clause()}
        ),
        conditions as (
            select c.condition_key
            from fact_condition as c
            inner join dim_patient as p on c.patient_key = p.patient_key
            inner join dim_date as d on c.onset_date_key = d.date_key
            where d.year between ? and ?
              and {_gender_clause()}
        ),
        observations as (
            select o.observation_key
            from fact_observation as o
            inner join dim_patient as p on o.patient_key = p.patient_key
            inner join dim_date as d on o.date_key = d.date_key
            where d.year between ? and ?
              and {_gender_clause()}
        )
        select
            (select count(distinct patient_key) from encounters) as patients,
            (select count(*) from encounters) as encounters,
            (select count(*) from conditions) as conditions,
            (select count(*) from observations) as observations
        """,
        [year_start, year_end, gender, gender] * 3,
    )
    row = frame.iloc[0]
    return {column: int(row[column]) for column in frame.columns}


@st.cache_data
def load_encounters_per_year(gender: str, year_start: int, year_end: int) -> pd.DataFrame:
    return query(
        f"""
        select
            d.year,
            t.class_code,
            count(*) as encounter_count
        from fact_encounter as e
        inner join dim_patient as p on e.patient_key = p.patient_key
        inner join dim_date as d on e.start_date_key = d.date_key
        inner join dim_encounter_type as t on e.encounter_type_key = t.encounter_type_key
        where d.year between ? and ?
          and {_gender_clause()}
          and t.class_code is not null
        group by d.year, t.class_code
        order by d.year, t.class_code
        """,
        [year_start, year_end, gender, gender],
    )


@st.cache_data
def load_top_conditions(gender: str, year_start: int, year_end: int) -> pd.DataFrame:
    return query(
        f"""
        select
            c.display as condition,
            count(distinct f.patient_key) as patient_count
        from fact_condition as f
        inner join dim_condition_code as c on f.condition_code_key = c.condition_code_key
        inner join dim_patient as p on f.patient_key = p.patient_key
        inner join dim_date as d on f.onset_date_key = d.date_key
        where d.year between ? and ?
          and {_gender_clause()}
          and c.condition_code_key <> '-1'
          and c.display is not null
        group by c.display
        order by patient_count desc
        limit 10
        """,
        [year_start, year_end, gender, gender],
    )


@st.cache_data
def load_condition_status(gender: str, year_start: int, year_end: int) -> pd.DataFrame:
    # In this extract, is_active false is exactly clinical_status 'resolved'.
    return query(
        f"""
        select
            case when f.is_active then 'Active' else 'Resolved' end as status,
            count(*) as condition_count
        from fact_condition as f
        inner join dim_patient as p on f.patient_key = p.patient_key
        inner join dim_date as d on f.onset_date_key = d.date_key
        where d.year between ? and ?
          and {_gender_clause()}
        group by status
        order by status
        """,
        [year_start, year_end, gender, gender],
    )


@st.cache_data
def load_duration_by_class(gender: str, year_start: int, year_end: int) -> pd.DataFrame:
    return query(
        f"""
        select
            t.class_code,
            round(avg(e.duration_minutes), 1) as avg_duration_minutes
        from fact_encounter as e
        inner join dim_patient as p on e.patient_key = p.patient_key
        inner join dim_date as d on e.start_date_key = d.date_key
        inner join dim_encounter_type as t on e.encounter_type_key = t.encounter_type_key
        where d.year between ? and ?
          and {_gender_clause()}
          and t.class_code is not null
          and e.duration_minutes is not null
        group by t.class_code
        order by t.class_code
        """,
        [year_start, year_end, gender, gender],
    )


@st.cache_data
def load_bmi_by_gender_age(gender: str, year_start: int, year_end: int) -> pd.DataFrame:
    """Same two-step average as sql/bmi_by_gender_age.sql, plus the sidebar filters."""
    return query(
        f"""
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
            from fact_observation as f
            inner join dim_observation_code as c
                on f.observation_code_key = c.observation_code_key
            inner join dim_patient as p
                on f.patient_key = p.patient_key
            inner join dim_date as d
                on f.date_key = d.date_key
            where c.loinc_code = '39156-5'
              and f.value_numeric is not null
              and f.age_at_observation is not null
              and p.patient_key <> '-1'
              and d.year between ? and ?
              and {_gender_clause()}
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
        """,
        [year_start, year_end, gender, gender],
    )


def _show_chart(frame: pd.DataFrame, figure) -> None:
    if frame.empty:
        st.info("No rows for this filter.")
        return
    st.plotly_chart(figure, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="FHIR clinical warehouse", layout="wide")
    st.title("FHIR clinical warehouse")

    if not WAREHOUSE.exists():
        st.error(f"Warehouse not found: {WAREHOUSE}. Run make transform first.")
        st.stop()

    year_min, year_max = load_year_bounds()
    gender = st.sidebar.selectbox("Gender", ["All", *load_genders()])
    year_start, year_end = st.sidebar.slider(
        "Year",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
    )

    kpis = load_kpis(gender, year_start, year_end)
    patient_col, encounter_col, condition_col, observation_col = st.columns(4)
    patient_col.metric("Patients", f"{kpis['patients']:,}")
    encounter_col.metric("Encounters", f"{kpis['encounters']:,}")
    condition_col.metric("Conditions", f"{kpis['conditions']:,}")
    observation_col.metric("Observations", f"{kpis['observations']:,}")

    encounters = load_encounters_per_year(gender, year_start, year_end)
    conditions = load_top_conditions(gender, year_start, year_end)
    left, right = st.columns(2)
    with left:
        st.subheader("Encounters per year")
        if encounters.empty:
            st.info("No rows for this filter.")
        else:
            _show_chart(
                encounters,
                px.line(
                    encounters,
                    x="year",
                    y="encounter_count",
                    color="class_code",
                    category_orders={"class_code": CLASS_ORDER},
                    labels={"year": "Year", "encounter_count": "Encounters", "class_code": "Class"},
                ),
            )
    with right:
        st.subheader("Top 10 conditions")
        if conditions.empty:
            st.info("No rows for this filter.")
        else:
            _show_chart(
                conditions,
                px.bar(
                    conditions.sort_values("patient_count", ascending=True),
                    x="patient_count",
                    y="condition",
                    orientation="h",
                    labels={"patient_count": "Patients", "condition": ""},
                ),
            )

    status = load_condition_status(gender, year_start, year_end)
    duration = load_duration_by_class(gender, year_start, year_end)
    left, right = st.columns(2)
    with left:
        st.subheader("Active vs resolved conditions")
        if status.empty:
            st.info("No rows for this filter.")
        else:
            _show_chart(
                status,
                px.bar(
                    status,
                    x="status",
                    y="condition_count",
                    labels={"status": "", "condition_count": "Conditions"},
                ),
            )
    with right:
        st.subheader("Average encounter duration")
        if duration.empty:
            st.info("No rows for this filter.")
        else:
            _show_chart(
                duration,
                px.bar(
                    duration,
                    x="class_code",
                    y="avg_duration_minutes",
                    category_orders={"class_code": CLASS_ORDER},
                    labels={"class_code": "Class", "avg_duration_minutes": "Minutes"},
                ),
            )

    st.subheader("BMI by gender and age")
    st.caption(BMI_NOTE)
    bmi = load_bmi_by_gender_age(gender, year_start, year_end)
    if bmi.empty:
        st.info("No rows for this filter.")
    else:
        bmi["age_bracket"] = pd.Categorical(bmi["age_bracket"], AGE_BRACKETS, ordered=True)
        bmi = bmi.sort_values(["age_bracket", "gender"])
        _show_chart(
            bmi,
            px.bar(
                bmi,
                x="age_bracket",
                y="avg_bmi",
                color="gender",
                barmode="group",
                labels={"age_bracket": "Age", "avg_bmi": "Average BMI", "gender": "Gender"},
            ),
        )
    if not bmi.empty:
        st.dataframe(
            bmi,
            hide_index=True,
            use_container_width=True,
            column_config={
                "gender": "Gender",
                "age_bracket": "Age bracket",
                "avg_bmi": st.column_config.NumberColumn("Average BMI", format="%.1f"),
                "patient_count": "Patients",
                "reading_count": "Readings",
            },
        )


if __name__ == "__main__":
    main()
