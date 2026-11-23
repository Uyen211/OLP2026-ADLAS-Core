/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type {
  ForgotPasswordResponse,
  LoginRequest,
  LoginResponse,
  MeResponse,
  MfaSetupResponse,
  MfaVerifyRequest,
  ResetPasswordRequest,
  TokenResponse,
} from "../types/auth";
import { httpRequest } from "./httpClient";

export const authService = {
  login(payload: LoginRequest): Promise<LoginResponse> {
    return httpRequest<LoginResponse>("/auth/login", {
      method: "POST",
      body: payload,
      skipAuth: true,
      skipAuthRefresh: true,
    });
  },

  verifyMfa(payload: MfaVerifyRequest): Promise<TokenResponse> {
    return httpRequest<TokenResponse>("/auth/mfa/verify", {
      method: "POST",
      body: payload,
      skipAuth: true,
      skipAuthRefresh: true,
    });
  },

  refresh(refreshToken: string): Promise<TokenResponse> {
    return httpRequest<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      skipAuth: true,
      skipAuthRefresh: true,
    });
  },

  getMe(): Promise<MeResponse> {
    return httpRequest<MeResponse>("/auth/me", { method: "GET" });
  },

  logout(): Promise<void> {
    return httpRequest<void>("/auth/logout", {
      method: "POST",
      skipAuthRefresh: true,
    });
  },

  setupMfa(): Promise<MfaSetupResponse> {
    return httpRequest<MfaSetupResponse>("/auth/mfa/setup", { method: "POST" });
  },

  enableMfa(code: string): Promise<void> {
    return httpRequest<void>("/auth/mfa/enable", {
      method: "POST",
      body: { code },
    });
  },

  disableMfa(code: string): Promise<void> {
    return httpRequest<void>("/auth/mfa/disable", {
      method: "POST",
      body: { code },
    });
  },

  forgotPassword(email: string): Promise<ForgotPasswordResponse> {
    return httpRequest<ForgotPasswordResponse>("/auth/password/forgot", {
      method: "POST",
      body: { email },
      skipAuth: true,
      skipAuthRefresh: true,
    });
  },

  resetPassword(payload: ResetPasswordRequest): Promise<void> {
    return httpRequest<void>("/auth/password/reset", {
      method: "POST",
      body: payload,
      skipAuth: true,
      skipAuthRefresh: true,
    });
  },
};
