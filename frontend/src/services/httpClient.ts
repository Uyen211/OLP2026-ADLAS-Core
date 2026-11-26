/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import { resolveErrorMessage } from "../apps/main-app/constants/errorMessages";
import type { TokenResponse } from "../types/auth";

export const API_BASE_URL = (
  (import.meta.env.VITE_BACKEND_API_URL as string | undefined) || "/api/v1"
).replace(/\/+$/, "");

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly field?: string;
  public readonly remainingAttempts?: number;
  public readonly retryAfterSeconds?: number;
  public readonly lockedUntil?: string;
  public readonly missingColumns?: string[];
  public readonly rawDetail?: unknown;

  constructor(params: {
    status: number;
    code: string;
    message: string;
    field?: string;
    remainingAttempts?: number;
    retryAfterSeconds?: number;
    lockedUntil?: string;
    missingColumns?: string[];
    rawDetail?: unknown;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.code = params.code;
    this.field = params.field;
    this.remainingAttempts = params.remainingAttempts;
    this.retryAfterSeconds = params.retryAfterSeconds;
    this.lockedUntil = params.lockedUntil;
    this.missingColumns = params.missingColumns;
    this.rawDetail = params.rawDetail;
  }
}

interface AuthSessionBridge {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  onTokensRefreshed: (tokens: TokenResponse) => void;
  onAuthFailure: () => void;
}

let sessionBridge: AuthSessionBridge | null = null;
let inflightRefresh: Promise<string | null> | null = null;

export function registerAuthSessionBridge(bridge: AuthSessionBridge): void {
  sessionBridge = bridge;
}

interface FastApiValidationItem {
  type?: string;
  loc?: Array<string | number>;
  msg?: string;
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  const detail =
    body && typeof body === "object" && "detail" in body
      ? (body as { detail: unknown }).detail
      : body;

  // Structured ADLASException payload: { detail: { code, message, ... } }
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const obj = detail as Record<string, unknown>;
    const code = typeof obj.code === "string" ? obj.code : `HTTP_${response.status}`;
    const rawMsg = typeof obj.message === "string" ? obj.message : undefined;
    const message = resolveErrorMessage(code, rawMsg);

    return new ApiError({
      status: response.status,
      code,
      message,
      field: typeof obj.field === "string" ? obj.field : undefined,
      remainingAttempts:
        typeof obj.remaining_attempts === "number" ? obj.remaining_attempts : undefined,
      retryAfterSeconds:
        typeof obj.retry_after_seconds === "number" ? obj.retry_after_seconds : undefined,
      lockedUntil: typeof obj.locked_until === "string" ? obj.locked_until : undefined,
      missingColumns: Array.isArray(obj.missing_columns)
        ? obj.missing_columns.filter((v): v is string => typeof v === "string")
        : undefined,
      rawDetail: detail,
    });
  }

  // FastAPI default 422 validation error array -> map missing to E-1, others to E-2
  if (response.status === 422 && Array.isArray(detail) && detail.length > 0) {
    const items = detail as FastApiValidationItem[];
    const hasMissing = items.some((item) => item.type === "missing");
    const code = hasMissing ? "E-1" : "E-2";
    const first = items[0];
    const lastLoc =
      Array.isArray(first.loc) && first.loc.length > 0
        ? String(first.loc[first.loc.length - 1])
        : undefined;

    return new ApiError({
      status: response.status,
      code,
      message: resolveErrorMessage(code),
      field: lastLoc,
      rawDetail: detail,
    });
  }

  if (typeof detail === "string" && detail.trim().length > 0) {
    return new ApiError({
      status: response.status,
      code: `HTTP_${response.status}`,
      message: detail,
      rawDetail: detail,
    });
  }

  return new ApiError({
    status: response.status,
    code: `HTTP_${response.status}`,
    message: resolveErrorMessage(undefined),
    rawDetail: detail,
  });
}

async function attemptTokenRefresh(): Promise<string | null> {
  if (!sessionBridge) return null;
  const refreshToken = sessionBridge.getRefreshToken();
  if (!refreshToken) return null;

  if (!inflightRefresh) {
    inflightRefresh = (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) {
          sessionBridge?.onAuthFailure();
          return null;
        }
        const data = (await res.json()) as TokenResponse;
        sessionBridge?.onTokensRefreshed(data);
        return data.access_token;
      } catch {
        sessionBridge?.onAuthFailure();
        return null;
      } finally {
        inflightRefresh = null;
      }
    })();
  }

  return inflightRefresh;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  formData?: FormData;
  headers?: Record<string, string>;
  skipAuth?: boolean;
  skipAuthRefresh?: boolean;
}

export async function httpRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const url = path.startsWith("http")
    ? path
    : `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;

  const execute = async (tokenOverride?: string | null): Promise<Response> => {
    const headers: Record<string, string> = { ...(options.headers ?? {}) };
    if (!options.formData && options.body !== undefined && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    if (!options.skipAuth) {
      const token =
        tokenOverride !== undefined ? tokenOverride : sessionBridge?.getAccessToken();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
    }

    try {
      return await fetch(url, {
        method: options.method ?? "GET",
        headers,
        body: options.formData
          ? options.formData
          : options.body !== undefined
            ? JSON.stringify(options.body)
            : undefined,
      });
    } catch {
      throw new ApiError({
        status: 0,
        code: "NETWORK_ERROR",
        message: resolveErrorMessage("NETWORK_ERROR"),
      });
    }
  };

  let response = await execute();

  if (
    response.status === 401 &&
    !options.skipAuth &&
    !options.skipAuthRefresh &&
    sessionBridge?.getRefreshToken()
  ) {
    const nextToken = await attemptTokenRefresh();
    if (nextToken) {
      response = await execute(nextToken);
    }
  }

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.text()) as unknown as T;
}

export async function httpFetchBlob(path: string): Promise<Blob> {
  const url = path.startsWith("http")
    ? path
    : path.startsWith("/api/")
      ? path
      : `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;

  const headers: Record<string, string> = {};
  const token = sessionBridge?.getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, { method: "GET", headers });
  if (!response.ok) {
    throw await parseErrorResponse(response);
  }
  return response.blob();
}

export async function httpFetchBlobUrl(path: string): Promise<string> {
  const blob = await httpFetchBlob(path);
  return URL.createObjectURL(blob);
}

export async function httpDownloadBlob(path: string, filename: string): Promise<void> {
  const blob = await httpFetchBlob(path);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
