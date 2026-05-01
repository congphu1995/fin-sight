export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function friendlyMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 504) return "Agent took too long. Try a more specific question.";
    if (err.status === 502) return "Model unavailable. Try again in a moment.";
    if (err.status === 404) return "Not found.";
    if (err.status >= 500) return "Backend error. Try again.";
    if (err.status === 400) return "Invalid request.";
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Unknown error";
}

type FetchOptions = Omit<RequestInit, "body"> & { body?: unknown; query?: Record<string, string | number | undefined> };

export async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { body, query, headers, ...rest } = opts;

  const search = new URLSearchParams();
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") search.set(k, String(v));
    }
  }
  const qs = search.toString();
  const url = `/api/v1${path}${qs ? `?${qs}` : ""}`;

  const response = await fetch(url, {
    ...rest,
    headers: {
      "content-type": "application/json",
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let parsed: unknown;
    try {
      parsed = await response.json();
    } catch {
      parsed = await response.text().catch(() => undefined);
    }
    const detail =
      (typeof parsed === "object" && parsed && "detail" in parsed && typeof parsed.detail === "string"
        ? parsed.detail
        : null) ?? `HTTP ${response.status}`;
    throw new ApiError(detail, response.status, parsed);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
