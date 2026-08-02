#!/usr/bin/env bash
set -Eeuo pipefail

mode="${1:?verification mode is required}"
test_contract="${2:-}"
[[ "${mode}" =~ ^(quick|standard|full)$ ]] || {
  printf 'invalid verification mode: %s\n' "${mode}" >&2
  exit 2
}

cp -a /candidate/. /tmp/source
python -m pip install --quiet --target /tmp/site '/tmp/source/backend[dev]'
export PYTHONPATH="/tmp/site:/tmp/source/backend"
export PATH="/tmp/site/bin:${PATH}"

cd /tmp/source/backend
python -m alembic upgrade head
python - <<'PY'
import os

from sqlalchemy import create_engine, text

engine = create_engine(os.environ["WAREHOUSE_DATABASE_URL"])
with engine.connect() as connection:
    role = connection.execute(
        text(
            "SELECT current_user, rolsuper, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        )
    ).mappings().one()
engine.dispose()
if role["rolsuper"] or role["rolbypassrls"]:
    raise SystemExit(f"unsafe verification application role: {role['current_user']}")
PY

if [[ "${mode}" == full ]]; then
  export WAREHOUSE_RUN_INTEGRATION_TESTS=1
fi

tests=()
if [[ -n "${test_contract}" ]]; then
  IFS=: read -r -a requested_tests <<< "${test_contract}"
  for target in "${requested_tests[@]}"; do
    [[ "${target}" =~ ^backend/tests([/][A-Za-z0-9_.-]+)?$ ]] || {
      printf 'unsafe verification test target: %s\n' "${target}" >&2
      exit 2
    }
    tests+=("${target#backend/}")
  done
fi
if [[ ${#tests[@]} -eq 0 ]]; then
  tests=(tests/test_config.py)
fi

python -m pytest -q "${tests[@]}"
