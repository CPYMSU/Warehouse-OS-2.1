/** Warehouse OS browser Data API SDK. No wak_ key or database DSN is used here. */
export class WarehouseDataClient {
  constructor({ projectKey, baseUrl = "https://bonfirework.org", persistence = "session" }) {
    if (!projectKey || !String(projectKey).startsWith("dbp_")) {
      throw new Error("A public dbp_ projectKey is required");
    }
    this.projectKey = String(projectKey);
    this.endpoint = `${String(baseUrl).replace(/\/$/, "")}/api/database-gateway/v1/projects/${encodeURIComponent(this.projectKey)}`;
    this.storage = persistence === "local" ? window.localStorage :
      persistence === "none" ? null : window.sessionStorage;
    this.storageKey = `warehouse-data:${this.projectKey.slice(-24)}`;
    this.session = this._load();
  }

  _load() {
    if (!this.storage) return null;
    try { return JSON.parse(this.storage.getItem(this.storageKey) || "null"); }
    catch { return null; }
  }

  _save(value) {
    this.session = value;
    if (!this.storage) return;
    if (value) this.storage.setItem(this.storageKey, JSON.stringify(value));
    else this.storage.removeItem(this.storageKey);
  }

  async connect({ forceNew = false } = {}) {
    const refreshToken = forceNew ? null : this.session?.refresh_token;
    const response = await fetch(`${this.endpoint}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(refreshToken ? { refresh_token: refreshToken } : {}),
    });
    if (!response.ok) {
      if (refreshToken && response.status === 401) {
        this._save(null);
        return this.connect({ forceNew: true });
      }
      throw await this._error(response);
    }
    const session = await response.json();
    this._save(session);
    return { subject: session.subject, expiresAt: session.expires_at };
  }

  async _accessToken() {
    const expiresAt = Date.parse(this.session?.expires_at || "");
    if (!this.session?.access_token || !Number.isFinite(expiresAt) || expiresAt < Date.now() + 30000) {
      await this.connect();
    }
    return this.session.access_token;
  }

  async _request(path, options = {}, retried = false) {
    const token = await this._accessToken();
    const response = await fetch(`${this.endpoint}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`,
      },
    });
    if (response.status === 401 && !retried) {
      await this.connect();
      return this._request(path, options, true);
    }
    if (!response.ok) throw await this._error(response);
    return response.status === 204 ? null : response.json();
  }

  async _error(response) {
    let payload;
    try { payload = await response.json(); }
    catch { payload = { detail: response.statusText }; }
    const error = new Error(typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail));
    error.status = response.status;
    error.payload = payload;
    return error;
  }

  list(collection, { limit = 100, offset = 0 } = {}) {
    const name = encodeURIComponent(collection);
    return this._request(`/data/${name}?limit=${limit}&offset=${offset}`);
  }

  get(collection, key) {
    return this._request(`/data/${encodeURIComponent(collection)}/${encodeURIComponent(key)}`);
  }

  set(collection, key, data, { expectedVersion = null } = {}) {
    const query = expectedVersion === null ? "" : `?expected_version=${encodeURIComponent(expectedVersion)}`;
    return this._request(`/data/${encodeURIComponent(collection)}/${encodeURIComponent(key)}${query}`, {
      method: "PUT",
      body: JSON.stringify({ data }),
    });
  }

  delete(collection, key) {
    return this._request(`/data/${encodeURIComponent(collection)}/${encodeURIComponent(key)}`, {
      method: "DELETE",
    });
  }

  disconnect() { this._save(null); }
}

export function createWarehouseDataClient(options) {
  return new WarehouseDataClient(options);
}
