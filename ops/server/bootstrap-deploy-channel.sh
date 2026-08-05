#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${EUID}" -eq 0 ]] || {
  printf 'bootstrap must run as root\n' >&2
  exit 1
}
[[ "$#" -eq 1 ]] || {
  printf 'usage: bootstrap-deploy-channel.sh "<ssh-ed25519 public key>"\n' >&2
  exit 1
}

public_key="$1"
[[ "${public_key}" == ssh-ed25519\ * ]] || {
  printf 'only an ssh-ed25519 public key is accepted\n' >&2
  exit 1
}

if ! id warehouse-deploy >/dev/null 2>&1; then
  useradd --create-home --home-dir /var/lib/warehouse-deploy \
    --shell /bin/bash warehouse-deploy
fi
passwd --lock warehouse-deploy >/dev/null 2>&1 || true

install -d -m 0750 -o warehouse-deploy -g warehouse-deploy \
  /var/lib/warehouse-deploy \
  /var/lib/warehouse-deploy/.ssh \
  /var/lib/warehouse-deploy/incoming

printf '%s %s\n' \
  'no-agent-forwarding,no-port-forwarding,no-X11-forwarding,no-pty' \
  "${public_key}" \
  > /var/lib/warehouse-deploy/.ssh/authorized_keys
chown warehouse-deploy:warehouse-deploy \
  /var/lib/warehouse-deploy/.ssh/authorized_keys
chmod 0600 /var/lib/warehouse-deploy/.ssh/authorized_keys

install -m 0755 /opt/warehouse-os/current/ops/server/warehouse-deploy \
  /usr/local/sbin/warehouse-deploy
install -d -m 0750 /run/warehouse-shield /opt/warehouse-os/shared/shield
env_file=/opt/warehouse-os/shared/.env.production
if ! grep -q '^WAREHOUSE_SHIELD_AGENT_TOKEN=' "${env_file}"; then
  printf 'WAREHOUSE_SHIELD_AGENT_TOKEN=%s\n' "$(openssl rand -hex 32)" >> "${env_file}"
fi
if ! grep -q '^WAREHOUSE_SHIELD_REPAIR_APPLY=' "${env_file}"; then
  printf 'WAREHOUSE_SHIELD_REPAIR_APPLY=false\n' >> "${env_file}"
fi
if ! grep -q '^WAREHOUSE_SHIELD_DATA_MOUNTPOINT=' "${env_file}"; then
  printf 'WAREHOUSE_SHIELD_DATA_MOUNTPOINT=/mnt/warehouse-data\n' >> "${env_file}"
fi
if ! grep -q '^WAREHOUSE_SHIELD_DATA_DEVICE=' "${env_file}"; then
  printf 'WAREHOUSE_SHIELD_DATA_DEVICE=/dev/vdb1\n' >> "${env_file}"
fi
if ! grep -q '^WAREHOUSE_SHIELD_DATA_VOLUME_REQUIRED=' "${env_file}"; then
  printf 'WAREHOUSE_SHIELD_DATA_VOLUME_REQUIRED=true\n' >> "${env_file}"
fi
chmod 0600 "${env_file}"
install -m 0755 /opt/warehouse-os/current/ops/server/warehouse-shield-agent.py \
  /usr/local/sbin/warehouse-shield-agent
install -m 0644 /opt/warehouse-os/current/infra/systemd/warehouse-shield-agent.service \
  /etc/systemd/system/warehouse-shield-agent.service
systemctl daemon-reload
systemctl enable --now warehouse-shield-agent.service
printf '%s\n' \
  'warehouse-deploy ALL=(root) NOPASSWD: /usr/local/sbin/warehouse-deploy *' \
  > /etc/sudoers.d/warehouse-deploy
chmod 0440 /etc/sudoers.d/warehouse-deploy
visudo -cf /etc/sudoers.d/warehouse-deploy >/dev/null

install -d -m 0755 /etc/nginx/snippets /opt/warehouse-os/shared/deploy-state
if [[ ! -f /etc/nginx/snippets/warehouse-api-upstream.conf ]]; then
  printf 'proxy_pass http://127.0.0.1:8080;\n' \
    > /etc/nginx/snippets/warehouse-api-upstream.conf
fi

nginx_site=/etc/nginx/sites-available/bonfirework.org
[[ -f "${nginx_site}" ]] || {
  printf 'nginx site not found: %s\n' "${nginx_site}" >&2
  exit 1
}
if ! grep -Fq '*.apps.bonfirework.org' "${nginx_site}"; then
  sed -i \
    's/server_name bonfirework\.org www\.bonfirework\.org;/server_name bonfirework.org www.bonfirework.org *.apps.bonfirework.org;/' \
    "${nginx_site}"
fi
if ! grep -q 'warehouse-api-upstream.conf' "${nginx_site}"; then
  sed -i \
    's@^[[:space:]]*proxy_pass http://127\.0\.0\.1:8080;@        include /etc/nginx/snippets/warehouse-api-upstream.conf;@' \
    "${nginx_site}"
fi
nginx -t
systemctl reload nginx

touch /var/log/warehouse-deployments.jsonl
chmod 0640 /var/log/warehouse-deployments.jsonl
printf 'deploy-channel=ready\n'
