#!/bin/bash
# Launch the CommerceOS Web COO Dashboard.
# Usage: ./run_dashboard.sh

set -e

cd "$(dirname "$0")"
source .venv/bin/activate

export PYTHONPATH="$(pwd)"

echo "Starting CommerceOS Web COO Dashboard..."
echo "Open: http://localhost:8501"

.venv/bin/python3 -m streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.headless true
