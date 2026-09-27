#!/usr/bin/env bash
# download -> extract -> dbt build -> Streamlit
set -euo pipefail

cd /app

bash scripts/download_data.sh
python -m src.extract.run_extract
( cd dbt && dbt build --profiles-dir . )

exec streamlit run app/streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port 8501
