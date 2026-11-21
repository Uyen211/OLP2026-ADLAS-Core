/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Radio,
  RefreshCw,
  RotateCw,
  Trash2,
  Zap,
} from "lucide-react";
import { Badge } from "../../../components/ui/Badge";
import { WorkflowService } from "../../../services/workflowService";
import {
  ActiveBackgroundTask,
  DeadLetterItem,
  OutboxEventItem,
} from "../../../types/workflow";

export const TaskQueueMonitor: React.FC = () => {
  const [events, setEvents] = useState<OutboxEventItem[]>([]);
  const [tasks, setTasks] = useState<ActiveBackgroundTask[]>([]);
  const [dlqItems, setDlqItems] = useState<DeadLetterItem[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const loadAllQueueData = useCallback(async () => {
    try {
      const [eventsData, tasksData, dlqData] = await Promise.all([
        WorkflowService.getOutboxEvents(15),
        WorkflowService.getActiveTasks(),
        WorkflowService.getDlqEvents(),
      ]);

      setEvents(eventsData);
      setTasks(tasksData);
      setDlqItems(dlqData);
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    }
  }, []);

  useEffect(() => {
    setIsLoading(true);
    loadAllQueueData().finally(() => setIsLoading(false));
  }, [loadAllQueueData]);

  // Handle Retry DLQ Event
  const handleRetryDlq = async (item: DeadLetterItem) => {
    setRetryingId(item.id);
    try {
      const res = await WorkflowService.retryDlqEvent(item.id);
      showNotification("success", res.message);
      loadAllQueueData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    } finally {
      setRetryingId(null);
    }
  };

  // Handle Discard DLQ Event
  const handleDiscardDlq = async (item: DeadLetterItem) => {
    if (!window.confirm(`Discard failed dead-letter event '${item.event_type}' (${item.id})?`)) {
      return;
    }

    try {
      await WorkflowService.discardDlqEvent(item.id);
      showNotification("success", `Dead-letter event ${item.id.slice(0, 8)} discarded.`);
      loadAllQueueData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <Radio className="w-6 h-6 text-blue-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Event Bus & Background Workers Monitor
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Transactional Outbox stream, heavy AI worker task pools, and Dead-Letter Queue failure recovery (Use Case T1-A-M0-04).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => loadAllQueueData()}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-pill shadow-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          className={`flex items-center gap-3 p-4 rounded-xl border text-sm transition-all ${
            notification.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600" />
          )}
          <span className="font-medium">{notification.message}</span>
        </div>
      )}

      {/* Dead-Letter Queue (DLQ) Alert Card (BR-SYS-09) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-rose-600" />
            <h3 className="font-bold text-slate-900 text-sm">Dead-Letter Queue (DLQ) Failure Isolation</h3>
          </div>
          <Badge variant={dlqItems.length > 0 ? "danger" : "success"}>
            {dlqItems.length > 0 ? `${dlqItems.length} FAILED EVENTS` : "QUEUE CLEAR"}
          </Badge>
        </div>

        <div className="mt-4">
          {dlqItems.length === 0 ? (
            <div className="p-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-700">No events currently isolated in DLQ</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Failed messages exceeding 3 Exponential Backoff retries (Rule BR-SYS-09) will be routed here for technical inspection.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {dlqItems.map((item) => (
                <div
                  key={item.id}
                  className="p-4 bg-rose-50/50 border border-rose-200 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-rose-900">{item.event_type}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-100 text-rose-800">
                        Attempts: {item.retry_attempts}/3
                      </span>
                    </div>
                    <p className="text-xs text-rose-700 font-mono">{item.error_message}</p>
                    <div className="text-[11px] text-slate-500">
                      ID: <span className="font-mono text-slate-700">{item.id}</span> | Isolated at:{" "}
                      {new Date(item.created_at).toLocaleTimeString()}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      type="button"
                      disabled={retryingId === item.id}
                      onClick={() => handleRetryDlq(item)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-pill shadow-sm transition-all disabled:opacity-50"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${retryingId === item.id ? "animate-spin" : ""}`} />
                      {retryingId === item.id ? "Re-dispatching..." : "Retry Event"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDiscardDlq(item)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-100 transition-colors"
                      title="Discard event"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Two Column Layout: Active Background Tasks & Live Outbox Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Active Background Tasks */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-slate-900 text-sm">Active Asynchronous Worker Tasks</h3>
            </div>
            <span className="text-xs font-mono text-slate-500">{tasks.length} executing</span>
          </div>

          <div className="mt-4 space-y-4">
            {tasks.map((t) => (
              <div key={t.task_id} className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-800">{t.name}</span>
                  <Badge variant="primary">{t.category}</Badge>
                </div>

                <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    style={{ width: `${t.progress_pct}%` }}
                    className="h-full bg-blue-600 rounded-full transition-all duration-500"
                  />
                </div>

                <div className="flex justify-between items-center text-[11px] text-slate-500 font-mono">
                  <span>Progress: {t.progress_pct}%</span>
                  <span>ETA: ~{t.eta_seconds}s</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Transactional Outbox Live Stream (BR-SYS-08) */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-sm">Transactional Outbox Stream (SSE)</h3>
              </div>
              <Badge variant="success">ZERO LOSS</Badge>
            </div>

            <div className="mt-4 divide-y divide-slate-100 max-h-80 overflow-y-auto pr-1">
              {events.map((ev) => (
                <div key={ev.id} className="py-2.5 flex items-start justify-between gap-3 text-xs">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-900">{ev.event_type}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                        {ev.aggregate_type}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono truncate max-w-xs">
                      {JSON.stringify(ev.payload)}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <span className="font-mono text-[10px] text-slate-400">
                      {new Date(ev.created_at).toLocaleTimeString()}
                    </span>
                    <div className="mt-0.5">
                      <Badge variant="success">{ev.status}</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-3 mt-3 border-t border-slate-100 text-[11px] text-slate-400 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-500" />
            <span>Guaranteed at-least-once delivery via ACID transaction piggybacking (Rule BR-SYS-08).</span>
          </div>
        </div>
      </div>
    </div>
  );
};
