/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import {
  AddIpWhitelistPayload,
  GatewayMetrics,
  IpWhitelistEntry,
  RateLimitConfig,
  RateLimitUpdatePayload,
  ServiceModuleHealth,
} from "../types/gateway";

const BASE_URL = import.meta.env.VITE_BACKEND_API_URL || "/api/v1";

export class GatewayService {
  private static getHeaders(): HeadersInit {
    const token = localStorage.getItem("adlas_token");
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  /**
   * Fetch real-time gateway metrics.
   */
  static async getMetrics(): Promise<GatewayMetrics> {
    const response = await fetch(`${BASE_URL}/system/gateway/metrics`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch gateway metrics.");
    }
    return response.json();
  }

  /**
   * Probe health status of all 5 modular subsystems.
   */
  static async getModulesHealth(): Promise<ServiceModuleHealth[]> {
    const response = await fetch(`${BASE_URL}/system/gateway/health`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch service modules health.");
    }
    return response.json();
  }

  /**
   * Emergency restart a stalled service module (AC-03).
   */
  static async restartModule(moduleId: string): Promise<{
    module_id: string;
    status: string;
    message: string;
  }> {
    const response = await fetch(`${BASE_URL}/system/gateway/modules/${moduleId}/restart`, {
      method: "POST",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to restart module '${moduleId}'.`);
    }
    return response.json();
  }

  /**
   * Retrieve dynamic edge rate limit configuration.
   */
  static async getRateLimits(): Promise<RateLimitConfig> {
    const response = await fetch(`${BASE_URL}/system/gateway/rate-limits`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch rate limit settings.");
    }
    return response.json();
  }

  /**
   * Update edge rate limits (enforces E-GATEWAY-02 and BR-GATEWAY-01).
   */
  static async updateRateLimits(payload: RateLimitUpdatePayload): Promise<RateLimitConfig> {
    const response = await fetch(`${BASE_URL}/system/gateway/rate-limits`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update rate limit policies.");
    }
    return response.json();
  }

  /**
   * List authorized exam room CIDRs.
   */
  static async listIpWhitelist(): Promise<IpWhitelistEntry[]> {
    const response = await fetch(`${BASE_URL}/system/gateway/ip-whitelist`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch exam IP whitelist.");
    }
    return response.json();
  }

  /**
   * Register a new exam room CIDR block (enforces E-SYS-02).
   */
  static async addIpWhitelist(payload: AddIpWhitelistPayload): Promise<IpWhitelistEntry> {
    const response = await fetch(`${BASE_URL}/system/gateway/ip-whitelist`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to add IP whitelist entry.");
    }
    return response.json();
  }

  /**
   * Remove a CIDR block from the exam room whitelist.
   */
  static async deleteIpWhitelist(entryId: string): Promise<void> {
    const response = await fetch(`${BASE_URL}/system/gateway/ip-whitelist/${entryId}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to delete IP whitelist entry.");
    }
  }
}
