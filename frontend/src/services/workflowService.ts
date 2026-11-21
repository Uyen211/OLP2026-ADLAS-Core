/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import {
  ActiveBackgroundTask,
  CoreInfrastructureHealth,
  DeadLetterItem,
  OutboxEventItem,
  PaginatedAuditLogsResponse,
} from "../types/workflow";

const BASE_URL = import.meta.env.VITE_BACKEND_API_URL || "/api/v1";

export class WorkflowService {
  private static getHeaders(): HeadersInit {
    const token = localStorage.getItem("adlas_token");
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  /**
   * Fetch recent Outbox events (BR-SYS-08).
   */
  static async getOutboxEvents(limit: number = 20): Promise<OutboxEventItem[]> {
    const response = await fetch(`${BASE_URL}/system/events/outbox?limit=${limit}`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch outbox events stream.");
    }
    return response.json();
  }

  /**
   * Fetch actively executing background worker tasks.
   */
  static async getActiveTasks(): Promise<ActiveBackgroundTask[]> {
    const response = await fetch(`${BASE_URL}/system/tasks/active`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch active background tasks.");
    }
    return response.json();
  }

  /**
   * Fetch Dead-Letter Queue items (BR-SYS-09).
   */
  static async getDlqEvents(): Promise<DeadLetterItem[]> {
    const response = await fetch(`${BASE_URL}/system/tasks/dlq`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch dead-letter queue.");
    }
    return response.json();
  }

  /**
   * Re-queue and retry a dead-letter event.
   */
  static async retryDlqEvent(dlqId: string): Promise<{
    dlq_id: string;
    status: string;
    message: string;
  }> {
    const response = await fetch(`${BASE_URL}/system/tasks/dlq/${dlqId}/retry`, {
      method: "POST",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to re-dispatch DLQ event.");
    }
    return response.json();
  }

  /**
   * Permanently discard an unrecoverable DLQ event.
   */
  static async discardDlqEvent(dlqId: string): Promise<void> {
    const response = await fetch(`${BASE_URL}/system/tasks/dlq/${dlqId}/discard`, {
      method: "POST",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to discard DLQ event.");
    }
  }

  /**
   * Probe health status of the 6 core Layer-1 infrastructure services (BR-SYS-10).
   */
  static async getInfrastructureHealth(): Promise<CoreInfrastructureHealth[]> {
    const response = await fetch(`${BASE_URL}/system/infrastructure/health`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to query infrastructure health probes.");
    }
    return response.json();
  }

  /**
   * Query immutable system audit logs (BR-SYS-11).
   */
  static async getAuditLogs(params: {
    module?: string;
    action?: string;
    severity?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PaginatedAuditLogsResponse> {
    const queryParams = new URLSearchParams();
    if (params.module) queryParams.set("module", params.module);
    if (params.action) queryParams.set("action", params.action);
    if (params.severity) queryParams.set("severity", params.severity);
    if (params.page) queryParams.set("page", String(params.page));
    if (params.pageSize) queryParams.set("page_size", String(params.pageSize));

    const response = await fetch(`${BASE_URL}/system/audit-logs?${queryParams.toString()}`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch system audit logs.");
    }
    return response.json();
  }
}
