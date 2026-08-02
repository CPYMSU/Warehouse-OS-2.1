#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/warehouse-os/backups}"
HOSTED_BACKUP_DIR="${HOSTED_BACKUP_DIR:-/mnt/warehouse-data/hosted/archive/database-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-warehouse-os-postgres-1}"
POSTGRES_DATABASE="${POSTGRES_DATABASE:-warehouse_os}"
POSTGRES_USER="${POSTGRES_USER:-warehouse_admin}"
HOSTED_POSTGRES_CONTAINER="${HOSTED_POSTGRES_CONTAINER:-warehouse-os-hosted-postgres}"
HOSTED_POSTGRES_USER="${HOSTED_POSTGRES_USER:-warehouse_hosted_admin}"
HOSTED_DATA_MOUNTPOINT="${HOSTED_DATA_MOUNTPOINT:-/mnt/warehouse-data}"
LOCK_FILE="${LOCK_FILE:-/run/lock/warehouse-postgres-backup.lock}"

mkdir -p "${BACKUP_DIR}"
exec 9>"${LOCK_FILE}"
flock -n 9 || exit 0

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_dump="/tmp/warehouse-os-${stamp}.dump"
host_dump="${BACKUP_DIR}/warehouse-os-${stamp}.dump"
partial_dump="${host_dump}.partial"
hosted_container_dir="/tmp/warehouse-hosted-${stamp}"
hosted_final_dir="${HOSTED_BACKUP_DIR}/warehouse-hosted-${stamp}"
hosted_partial_dir="${hosted_final_dir}.partial"
hosted_created="not-configured"

cleanup() {
  docker exec "${POSTGRES_CONTAINER}" rm -f "${container_dump}" >/dev/null 2>&1 || true
  docker exec "${HOSTED_POSTGRES_CONTAINER}" rm -rf "${hosted_container_dir}" >/dev/null 2>&1 || true
  rm -f "${partial_dump}"
  rm -rf "${hosted_partial_dir}"
}
trap cleanup EXIT

docker exec "${POSTGRES_CONTAINER}" \
  pg_dump \
  --username="${POSTGRES_USER}" \
  --dbname="${POSTGRES_DATABASE}" \
  --format=custom \
  --compress=9 \
  --file="${container_dump}"

docker cp "${POSTGRES_CONTAINER}:${container_dump}" "${partial_dump}" >/dev/null
test -s "${partial_dump}"
mv "${partial_dump}" "${host_dump}"
chmod 600 "${host_dump}"
sha256sum "${host_dump}" > "${host_dump}.sha256"
chmod 600 "${host_dump}.sha256"

hosted_databases=()
if docker inspect "${HOSTED_POSTGRES_CONTAINER}" >/dev/null 2>&1; then
  mountpoint -q "${HOSTED_DATA_MOUNTPOINT}" || {
    printf 'hosted data mount is unavailable: %s\n' "${HOSTED_DATA_MOUNTPOINT}" >&2
    exit 1
  }
  mkdir -p "${HOSTED_BACKUP_DIR}"
  chmod 0700 "${HOSTED_BACKUP_DIR}"
  hosted_state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${HOSTED_POSTGRES_CONTAINER}")"
  [[ "${hosted_state}" == healthy ]] || {
    printf 'hosted PostgreSQL is not healthy: %s\n' "${hosted_state}" >&2
    exit 1
  }

  while IFS= read -r database_name; do
    [[ -n "${database_name}" ]] || continue
    [[ "${database_name}" =~ ^whdb_[0-9a-f]{32}$ ]] || {
      printf 'refusing unexpected hosted database name: %s\n' "${database_name}" >&2
      exit 1
    }
    hosted_databases+=("${database_name}")
  done < <(
    docker exec "${HOSTED_POSTGRES_CONTAINER}" psql \
      --username="${HOSTED_POSTGRES_USER}" --dbname=postgres \
      --tuples-only --no-align \
      --command="SELECT datname FROM pg_database WHERE datname LIKE 'whdb_%' ORDER BY datname"
  )

  mkdir -p "${hosted_partial_dir}"
  docker exec "${HOSTED_POSTGRES_CONTAINER}" mkdir -p "${hosted_container_dir}"
  docker exec "${HOSTED_POSTGRES_CONTAINER}" pg_dumpall \
    --username="${HOSTED_POSTGRES_USER}" --globals-only \
    --file="${hosted_container_dir}/globals.sql"
  docker cp \
    "${HOSTED_POSTGRES_CONTAINER}:${hosted_container_dir}/globals.sql" \
    "${hosted_partial_dir}/globals.sql" >/dev/null

  for database_name in "${hosted_databases[@]}"; do
    container_hosted_dump="${hosted_container_dir}/${database_name}.dump"
    docker exec "${HOSTED_POSTGRES_CONTAINER}" pg_dump \
      --username="${HOSTED_POSTGRES_USER}" --dbname="${database_name}" \
      --format=custom --compress=9 --file="${container_hosted_dump}"
    docker cp \
      "${HOSTED_POSTGRES_CONTAINER}:${container_hosted_dump}" \
      "${hosted_partial_dir}/${database_name}.dump" >/dev/null
  done

  {
    printf 'schema=warehouse.hosted-database-backup.v1\n'
    printf 'created_at=%s\n' "${stamp}"
    printf 'database_count=%s\n' "${#hosted_databases[@]}"
    printf 'source_container=%s\n' "${HOSTED_POSTGRES_CONTAINER}"
    printf 'physical_medium=hdd\n'
  } > "${hosted_partial_dir}/manifest"
  (
    cd "${hosted_partial_dir}"
    sha256sum globals.sql manifest ./*.dump 2>/dev/null > SHA256SUMS \
      || sha256sum globals.sql manifest > SHA256SUMS
  )
  chmod -R go-rwx "${hosted_partial_dir}"
  mv "${hosted_partial_dir}" "${hosted_final_dir}"
  hosted_created="${hosted_final_dir}"
fi

find "${BACKUP_DIR}" -maxdepth 1 -type f \
  \( -name 'warehouse-os-*.dump' -o -name 'warehouse-os-*.dump.sha256' \) \
  -mtime "+${RETENTION_DAYS}" -delete

if [[ -d "${HOSTED_BACKUP_DIR}" ]]; then
  find "${HOSTED_BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d \
    -name 'warehouse-hosted-*' -mtime "+${RETENTION_DAYS}" -exec rm -rf -- {} +
fi

printf 'control_created=%s\ncontrol_bytes=%s\nhosted_created=%s\nhosted_database_count=%s\nretention_days=%s\n' \
  "${host_dump}" "$(stat -c %s "${host_dump}")" \
  "${hosted_created}" "${#hosted_databases[@]}" "${RETENTION_DAYS}"
