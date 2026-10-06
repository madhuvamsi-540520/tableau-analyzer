// Thin fetch wrapper. Manages a per-browser session id (stored in localStorage)
// sent as X-Session-Id so the backend can scope this session's jobs. The id is
// a scoping token, not a secret/credential.

const SESSION_KEY = "tat.sessionId";

export function getSessionId() {
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid =
      (window.crypto?.randomUUID && window.crypto.randomUUID().replace(/-/g, "")) ||
      Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

async function request(path, options = {}) {
  const headers = { "X-Session-Id": getSessionId(), ...(options.headers || {}) };
  const res = await fetch(`/api${path}`, { ...options, headers });

  // Adopt a server-assigned session id if we didn't have one.
  const sid = res.headers.get("X-Session-Id");
  if (sid) localStorage.setItem(SESSION_KEY, sid);

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/health"),
  listJobs: () => request("/jobs"),
  getJob: (id) => request(`/jobs/${encodeURIComponent(id)}`),
  deleteJob: (id) => request(`/jobs/${encodeURIComponent(id)}`, { method: "DELETE" }),
  upload: (fileList) => {
    const form = new FormData();
    Array.from(fileList).forEach((f) => form.append("files", f));
    // Do NOT set Content-Type; the browser sets the multipart boundary.
    return request("/jobs", { method: "POST", body: form });
  },
  downloadCustomSql: (jobId, dsIndex, sqlIndex, filename) =>
    _download(`/api/jobs/${jobId}/customsql/${dsIndex}/${sqlIndex}`, filename || "custom_sql.sql"),
  exportJob: (jobId, format, filename) =>
    _download(`/api/jobs/${jobId}/export?format=${format}`, filename),
  // On-demand DAX/M conversion for one calculation. `body` may carry an apiKey
  // when the user enables AI; it is sent per-request and never stored client-side.
  suggestDax: (jobId, body) =>
    request(`/jobs/${encodeURIComponent(jobId)}/dax`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }),
  // On-demand AI Rationalization Review. `body` may carry an apiKey when the user
  // enables AI; it is sent per-request and never stored client-side.
  rationalizationReview: (jobId, body) =>
    request(`/jobs/${encodeURIComponent(jobId)}/rationalization/ai-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }),
  // Preview what PBIP generation will produce (Migration Assessment tab).
  // `body` may carry {useLlm, apiKey}; the key is sent per-request, never stored.
  pbipPreview: (jobId, body) =>
    request(`/jobs/${encodeURIComponent(jobId)}/pbip/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }),
  // Generate + download the PBIP .zip. POST (not GET) so the optional apiKey is
  // in the body, never in the URL or logs.
  generatePbip: (jobId, body) =>
    _downloadPost(`/api/jobs/${encodeURIComponent(jobId)}/pbip`, body, "project.pbip.zip"),
};

// POST that streams back a file download (reads the server-provided filename).
async function _downloadPost(url, body, fallbackName) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "X-Session-Id": getSessionId(), "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    let detail = `Download failed (${res.status})`;
    try {
      const b = await res.json();
      detail = b.detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const match = cd.match(/filename="?([^"]+)"?/i);
  const name = match ? match[1] : fallbackName || "download";
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = name;
  a.click();
  URL.revokeObjectURL(objectUrl);
}

async function _download(url, fallbackName) {
  const res = await fetch(url, { headers: { "X-Session-Id": getSessionId() } });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob = await res.blob();
  // Prefer the server-provided filename.
  const cd = res.headers.get("content-disposition") || "";
  const match = cd.match(/filename="?([^"]+)"?/i);
  const name = match ? match[1] : fallbackName || "download";
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = name;
  a.click();
  URL.revokeObjectURL(objectUrl);
}
