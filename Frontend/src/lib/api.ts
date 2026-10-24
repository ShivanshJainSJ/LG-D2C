const API_BASE = "/api/v1";

export interface UserSession {
  token: string;
  role: "ADMIN" | "AGENT";
  userId: string;
  fullName: string;
  email: string;
}

export function getStoredSession(): UserSession | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("lg_token");
  const role = localStorage.getItem("lg_role") as "ADMIN" | "AGENT";
  const userId = localStorage.getItem("lg_user_id");
  const fullName = localStorage.getItem("lg_user_name");
  const email = localStorage.getItem("lg_email");

  if (!token || !role) return null;
  return { token, role, userId: userId || "", fullName: fullName || "", email: email || "" };
}

export function setStoredSession(session: UserSession) {
  if (typeof window === "undefined") return;
  localStorage.setItem("lg_token", session.token);
  localStorage.setItem("lg_role", session.role);
  localStorage.setItem("lg_user_id", session.userId);
  localStorage.setItem("lg_user_name", session.fullName);
  localStorage.setItem("lg_email", session.email);
}

export function clearStoredSession() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("lg_token");
  localStorage.removeItem("lg_role");
  localStorage.removeItem("lg_user_id");
  localStorage.removeItem("lg_user_name");
  localStorage.removeItem("lg_email");
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const session = getStoredSession();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (session?.token) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearStoredSession();
    if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    let errorDetail = "An error occurred";
    try {
      const errJson = await response.json();
      if (typeof errJson.detail === "string") {
        errorDetail = errJson.detail;
      } else if (Array.isArray(errJson.detail)) {
        errorDetail = errJson.detail
          .map((e: any) => `${e.loc ? e.loc.filter((l: any) => l !== "body").join(".") : "field"}: ${e.msg}`)
          .join(", ");
      } else if (errJson.message) {
        errorDetail = errJson.message;
      } else {
        errorDetail = JSON.stringify(errJson);
      }
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }

  // Handle binary/blob responses
  const contentType = response.headers.get("content-type");
  if (contentType && (contentType.includes("application/pdf") || contentType.includes("image/"))) {
    return (await response.blob()) as unknown as T;
  }

  return response.json();
}

export const api = {
  get: <T>(url: string) => request<T>(url, { method: "GET" }),
  post: <T>(url: string, data?: any) =>
    request<T>(url, {
      method: "POST",
      body: data instanceof FormData ? data : JSON.stringify(data),
    }),
  put: <T>(url: string, data?: any) =>
    request<T>(url, {
      method: "PUT",
      body: data instanceof FormData ? data : JSON.stringify(data),
    }),
  delete: <T>(url: string) => request<T>(url, { method: "DELETE" }),
  download: async (url: string, defaultFilename: string) => {
    const session = getStoredSession();
    const headers = new Headers();
    if (session?.token) {
      headers.set("Authorization", `Bearer ${session.token}`);
    }
    const res = await fetch(`${API_BASE}${url}`, { headers });
    if (!res.ok) {
      let errText = "Failed to download file";
      try {
        const errJson = await res.json();
        if (errJson.detail) errText = errJson.detail;
      } catch {}
      throw new Error(errText);
    }
    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    const disposition = res.headers.get("content-disposition");
    let filename = defaultFilename;
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename=(.+)/);
      if (match && match[1]) filename = match[1].replace(/["']/g, "").trim();
    }
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);
  },
};
