import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const TOKEN_KEY = "pharmatrace.token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: the session lasts until reload */
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** FastAPI returns either {detail: "text"} or {detail: [{loc, msg}, ...]} for validation errors. */
function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => {
        const field = d.loc?.filter((p) => p !== "body").join(".");
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return `Request failed (${status})`;
}

export async function api<T = any>(path: string, options: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body = options.body;
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  }
  const res = await fetch(`/api${path}`, { ...options, headers, body });
  if (res.status === 401 && path !== "/auth/login") {
    setToken(null);
    window.location.href = "/login";
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, errorMessage(data, res.status));
  return data as T;
}

export function useApi<T = any>(path: string | null, refetchInterval?: number) {
  return useQuery<T>({
    queryKey: [path],
    queryFn: () => api<T>(path!),
    enabled: path !== null,
    refetchInterval,
  });
}

/** POST/PATCH/PUT/DELETE with a toast on success or error, then refresh every cached query. */
export function useAction<V = unknown>(
  method: string,
  path: (vars: V) => string,
  success?: string,
  onDone?: (data: any) => void,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: V) =>
      api(path(vars), { method, json: method === "DELETE" ? undefined : (vars as any)?.body ?? vars }),
    onSuccess: (data) => {
      if (success) notifications.show({ color: "teal", message: success });
      qc.invalidateQueries();
      onDone?.(data);
    },
    onError: (e: Error) => notifications.show({ color: "red", title: "Not saved", message: e.message, autoClose: 8000 }),
  });
}
