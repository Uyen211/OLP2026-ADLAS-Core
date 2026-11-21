/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  Activity,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "../../../components/ui/Badge";
import { WorkflowService } from "../../../services/workflowService";
import {
  CoreInfrastructureHealth,
  PaginatedAuditLogsResponse,
} from "../../../types/workflow";

export const HealthDashboard: React.FC = () => {
  const [healthList, setHealthList] = useState<CoreInfrastructureHealth[]>([]);
  const [auditLogsData, setAuditLogsData] = useState<PaginatedAuditLogsResponse>({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 1,
  });

  // Filter States
  const [moduleFilter, setModuleFilter] = useState("");
  const [actionQuery, setActionQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const [isLoading, setIsLoading] = useState(false);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [probes, logs] = await Promise.all([
        WorkflowService.getInfrastructureHealth(),
        WorkflowService.getAuditLogs({
          module: moduleFilter || undefined,
          action: actionQuery || undefined,
          severity: severityFilter || undefined,
          page: currentPage,
          pageSize: 20,
        }),
      ]);

      setHealthList(probes);
      setAuditLogsData(logs);
    } catch {
      // handled
    } finally {
      setIsLoading(false);
    }
  }, [moduleFilter, actionQuery, severityFilter, currentPage]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-6 h-6 text-blue-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Infrastructure Health & Immutable Audit Trail
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Real-time status probes for 6 core platform services and tamper-evident administrative audit trail (Use Case T1-A-M0-05).
          </p>
        </div>

        <button
          type="button"
          onClick={() => loadData()}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-pill shadow-sm transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          Probe Health
        </button>
      </div>

      {/* 6 Core Components Health Grid (Rule BR-SYS-10) */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Layer-1 Core Platform Services (Heartbeat Probes)
          </h2>
          <span className="text-xs font-mono text-emerald-600 font-medium">All 6 Subsystems Operational</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {healthList.map((probe) => (
            <div
              key={probe.component_id}
              className="p-5 bg-white rounded-2xl border border-slate-200 shadow-card flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-blue-600" />
                    <span className="font-bold text-sm text-slate-900">{probe.name}</span>
                  </div>
                  <span className="flex h-2.5 w-2.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                  </span>
                </div>

                <p className="text-xs font-mono text-slate-400 mt-1 truncate">{probe.endpoint}</p>

                <div className="mt-3 flex items-center gap-2 text-xs">
                  <Badge variant={probe.status === "HEALTHY" ? "success" : "danger"}>
                    {probe.status}
                  </Badge>
                  <span className="font-mono text-slate-500">{probe.latency_ms} ms</span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>Heartbeat: {new Date(probe.last_heartbeat).toLocaleTimeString()}</span>
                <span>Active</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Immutable Audit Trail Table (Rule BR-SYS-11) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">Immutable Audit Trail (Rule BR-SYS-11)</h3>
              <p className="text-[11px] text-slate-500">Append-only administrative operations log.</p>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="relative w-full md:w-48">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={actionQuery}
                onChange={(e) => {
                  setActionQuery(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Search action..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <select
              value={moduleFilter}
              onChange={(e) => {
                setModuleFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-700"
            >
              <option value="">Tất Cả Phân Hệ</option>
              <option value="identity">Identity</option>
              <option value="gateway">Gateway</option>
              <option value="storage">Storage</option>
              <option value="workflow">Workflow</option>
            </select>

            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-700"
            >
              <option value="">Tất Cả Mức Độ</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wider font-semibold border-b border-slate-100">
              <tr>
                <th className="px-6 py-3.5">Thời Gian Ghi Nhận</th>
                <th className="px-6 py-3.5">Actor</th>
                <th className="px-6 py-3.5">Action</th>
                <th className="px-6 py-3.5">Phân Hệ</th>
                <th className="px-6 py-3.5">Mức Độ</th>
                <th className="px-6 py-3.5">Source IP</th>
                <th className="px-6 py-3.5 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {auditLogsData.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-400 text-xs">
                    No audit records found matching current filter parameters.
                  </td>
                </tr>
              ) : (
                auditLogsData.items.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/70 transition-colors text-xs">
                    <td className="px-6 py-3.5 font-mono text-slate-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-3.5 font-semibold text-slate-800">
                      {log.actor_email || "System"}
                    </td>
                    <td className="px-6 py-3.5 font-mono font-medium text-slate-900">
                      {log.action}
                    </td>
                    <td className="px-6 py-3.5 font-mono text-slate-500 uppercase">
                      {log.module}
                    </td>
                    <td className="px-6 py-3.5">
                      <Badge
                        variant={
                          log.severity === "CRITICAL"
                            ? "danger"
                            : log.severity === "WARNING"
                            ? "warning"
                            : "neutral"
                        }
                      >
                        {log.severity}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5 font-mono text-slate-500">
                      {log.ip_address || "127.0.0.1"}
                    </td>
                    <td className="px-6 py-3.5 text-right font-mono text-[11px] text-slate-500 max-w-xs truncate">
                      {JSON.stringify(log.details)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
          <span>
            Total {auditLogsData.total} audit entries (Page {auditLogsData.page} of {auditLogsData.total_pages})
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={currentPage <= 1 || isLoading}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={currentPage >= auditLogsData.total_pages || isLoading}
              onClick={() => setCurrentPage((p) => p + 1)}
              className="px-3 py-1 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
