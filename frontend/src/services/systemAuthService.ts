/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import {
  PaginatedUsersResponse,
  RevokeSessionPayload,
  User,
  UserCreatePayload,
  UserSession,
  UserStatusUpdatePayload,
} from "../types/system";

const BASE_URL = import.meta.env.VITE_BACKEND_API_URL || "/api/v1";

export class SystemAuthService {
  private static getHeaders(): HeadersInit {
    const token = localStorage.getItem("adlas_token");
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  /**
   * Fetch paginated list of users with optional filtering.
   */
  static async listUsers(params: {
    query?: string;
    role?: string;
    isActive?: boolean;
    page?: number;
    pageSize?: number;
  }): Promise<PaginatedUsersResponse> {
    const queryParams = new URLSearchParams();
    if (params.query) queryParams.set("q", params.query);
    if (params.role) queryParams.set("role", params.role);
    if (params.isActive !== undefined) queryParams.set("is_active", String(params.isActive));
    if (params.page) queryParams.set("page", String(params.page));
    if (params.pageSize) queryParams.set("page_size", String(params.pageSize));

    const response = await fetch(`${BASE_URL}/system/auth/users?${queryParams.toString()}`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch users list");
    }

    return response.json();
  }

  /**
   * Create a new user account.
   */
  static async createUser(payload: UserCreatePayload): Promise<User> {
    const response = await fetch(`${BASE_URL}/system/auth/users`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to create user");
    }

    return response.json();
  }

  /**
   * Update active status (lock / unlock).
   */
  static async updateUserStatus(
    userId: string,
    payload: UserStatusUpdatePayload
  ): Promise<User> {
    const response = await fetch(`${BASE_URL}/system/auth/users/${userId}/status`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to update user status");
    }

    return response.json();
  }

  /**
   * Force revoke an active session.
   */
  static async revokeSession(payload: RevokeSessionPayload): Promise<{
    status: string;
    message: string;
  }> {
    const response = await fetch(`${BASE_URL}/system/auth/revoke-session`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to revoke session");
    }

    return response.json();
  }

  /**
   * Fetch active sessions for monitoring.
   */
  static async listActiveSessions(): Promise<UserSession[]> {
    const response = await fetch(`${BASE_URL}/system/auth/sessions`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      // If endpoint returns error or not ready, fallback to empty array
      return [];
    }

    return response.json();
  }
}
