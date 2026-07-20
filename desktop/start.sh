#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Sanal ortam yok. Oluşturuluyor..."
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -r requirements.txt
  pip install -r desktop/requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo ".env oluşturuldu — FLASK_SECRET_KEY ve OPENAI_API_KEY doldurun."
fi

echo "KipGPT masaüstü başlatılıyor..."
exec python desktop/main.py
