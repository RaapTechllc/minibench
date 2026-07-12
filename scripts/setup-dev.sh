#!/usr/bin/env bash
# MiniBench local dev setup — installs deps and prepares .env files.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> MiniBench dev setup"

# Python venv support (Debian/Ubuntu)
if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "Installing python3-venv..."
  sudo apt-get update -qq && sudo apt-get install -y -qq python3-venv python3-pip
fi

setup_venv() {
  local dir="$1"
  shift
  echo "  -> $dir"
  cd "$ROOT/$dir"
  rm -rf .venv
  python3 -m venv .venv
  # shellcheck disable=SC1091
  . .venv/bin/activate
  pip install -q "$@"
  deactivate
}

echo "==> Python virtualenvs"
setup_venv backend -r requirements.txt -r requirements-dev.txt
setup_venv cli -e . pytest
setup_venv agentbench -r requirements.txt -r requirements-dev.txt

echo "==> Frontend"
cd "$ROOT/frontend"
npm ci --silent

echo "==> Environment files"
if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "  Created .env from .env.example — add your OPENROUTER_API_KEY"
else
  echo "  .env already exists (unchanged)"
fi

if [[ ! -f "$ROOT/backend/.env" ]]; then
  cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
  echo "  Created backend/.env"
fi

if [[ ! -f "$ROOT/agentbench/.env" ]]; then
  cp "$ROOT/agentbench/.env.example" "$ROOT/agentbench/.env"
  echo "  Created agentbench/.env"
fi

echo ""
echo "Done. Next steps:"
echo "  1. Edit .env and set OPENROUTER_API_KEY (https://openrouter.ai/keys)"
echo "  2. Start Postgres: docker compose up -d db   (or use an existing instance on :5438)"
echo "  3. Backend:  cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 3070"
echo "  4. Frontend: cd frontend && npm run dev"
echo "  5. Agent dry-run (no key): python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run"
echo "  6. Agent live run: export OPENROUTER_API_KEY=sk-or-... && python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 3 --provider openrouter"
