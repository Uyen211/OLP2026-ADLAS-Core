/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { create } from "zustand";
import { clsx } from "clsx";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastStoreState {
  items: ToastItem[];
  push: (type: ToastType, message: string, durationMs?: number) => void;
  dismiss: (id: string) => void;
}

export const useToastStore = create<ToastStoreState>((set) => ({
  items: [],
  push: (type, message, durationMs = 4000) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    set((state) => ({ items: [...state.items, { id, type, message }] }));
    window.setTimeout(() => {
      set((state) => ({ items: state.items.filter((item) => item.id !== id) }));
    }, durationMs);
  },
  dismiss: (id) =>
    set((state) => ({ items: state.items.filter((item) => item.id !== id) })),
}));

export function showToast(type: ToastType, message: string): void {
  useToastStore.getState().push(type, message);
}

export const toast = {
  success: (message: string) => showToast("success", message),
  error: (message: string) => showToast("error", message),
  warning: (message: string) => showToast("warning", message),
  info: (message: string) => showToast("info", message),
};

const STYLE_BY_TYPE: Record<ToastType, string> = {
  success: "border-mm-success/30 bg-mm-success-bg text-mm-success",
  error: "border-mm-danger/30 bg-mm-danger-bg text-mm-danger",
  warning: "border-mm-warning/30 bg-mm-warning-bg text-mm-warning",
  info: "border-mm-blue-light bg-mm-bg text-mm-blue-deep",
};

export const ToastContainer: React.FC = () => {
  const { items, dismiss } = useToastStore();

  if (items.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed right-5 top-5 z-50 flex w-full max-w-sm flex-col gap-2.5"
    >
      {items.map((toast) => (
        <div
          key={toast.id}
          className={clsx(
            "flex items-start gap-3 rounded-mm-panel border px-4 py-3 shadow-mm-elevated",
            STYLE_BY_TYPE[toast.type]
          )}
        >
          {toast.type === "success" && <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />}
          {toast.type === "error" && <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />}
          {toast.type === "warning" && <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />}
          {toast.type === "info" && <Info className="mt-0.5 h-5 w-5 shrink-0" />}
          <p className="flex-1 font-mm-ui text-sm font-medium">{toast.message}</p>
          <button
            type="button"
            aria-label="Đóng thông báo"
            onClick={() => dismiss(toast.id)}
            className="rounded-full p-0.5 opacity-70 hover:opacity-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
};
