/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export type SystemRole = "ADMIN" | "USER";

export interface User {
  id: string;
  email: string;
  user_code: string;
  full_name: string;
  system_role: SystemRole;
  is_active: boolean;
  avatar_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedUsersResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserCreatePayload {
  email: string;
  user_code: string;
  full_name: string;
  system_role: SystemRole;
  initial_password?: string;
}

export interface UserStatusUpdatePayload {
  is_active: boolean;
  reason?: string;
}

export interface UserSession {
  session_id: string;
  user_id: string;
  email: string;
  user_code: string;
  full_name: string;
  system_role: SystemRole;
  ip_address: string;
  user_agent: string;
  issued_at: string;
  expires_at: string;
  status: "ACTIVE" | "REVOKED";
}

export interface RevokeSessionPayload {
  session_id: string;
  user_id: string;
  reason: string;
}
