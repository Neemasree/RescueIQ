#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[RescueIQ] Backend bootstrap starting..."

if [[ ! -d ".venv" ]]; then
  echo "[RescueIQ] Creating virtual environment at backend/.venv"
  python -m venv .venv
fi

source .venv/bin/activate

echo "[RescueIQ] Upgrading pip..."
python -m pip install --upgrade pip

echo "[RescueIQ] Installing requirements..."
pip install -r requirements.txt

echo "[RescueIQ] Starting backend server at http://0.0.0.0:${PORT:-8000}"
python -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
