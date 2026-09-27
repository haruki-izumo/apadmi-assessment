# Local pipeline. Docker runs the same steps via scripts/docker_entrypoint.sh.
.PHONY: download extract transform test docs app all clean

PYTHON ?= python
DBT ?= dbt
STREAMLIT ?= streamlit

download:
	bash scripts/download_data.sh

extract:
	$(PYTHON) -m src.extract.run_extract

transform:
	cd dbt && $(DBT) run --profiles-dir .

test:
	$(PYTHON) -m pytest tests -q
	cd dbt && $(DBT) test --profiles-dir .

docs:
	cd dbt && $(DBT) docs generate --profiles-dir .

app:
	$(STREAMLIT) run app/streamlit_app.py

all: download extract transform test
	@echo "Pipeline complete. Start the dashboard with: make app"

clean:
	@echo "Removing staging parquet and DuckDB warehouse..."
	rm -rf data/staging/*.parquet warehouse/fhir.duckdb
	rm -rf dbt/target dbt/logs dbt/dbt_packages
