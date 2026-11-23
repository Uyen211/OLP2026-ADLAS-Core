/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export type LandingTarget = "ADMIN_CONSOLE" | "TEACHING" | "LEARNING";

export interface CourseRoleClaim {
  course_id: string;
  role: string;
  course_code?: string | null;
  course_name?: string | null;
}

export interface MeResponse {
  id: string;
  email: string;
  user_code?: string | null;
  full_name: string;
  avatar_url?: string | null;
  system_role: string;
  mfa_enabled: boolean;
  course_roles: CourseRoleClaim[];
  landing: LandingTarget;
}

export interface LoginRequest {
  identifier: string;
  password: string;
  remember_me: boolean;
}

export interface LoginResponse {
  requires_mfa: boolean;
  mfa_token?: string | null;
  access_token?: string | null;
  refresh_token?: string | null;
  token_type: string;
  expires_in: number;
  user?: MeResponse | null;
}

export interface MfaVerifyRequest {
  mfa_token: string;
  code: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: MeResponse;
}

export interface MfaSetupResponse {
  secret: string;
  otpauth_uri: string;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
  confirm_password: string;
}
