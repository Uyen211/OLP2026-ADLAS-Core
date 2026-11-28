// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { CheckCircle2, RefreshCw, HardDrive, AlertCircle } from "lucide-react";
import type { AutosaveSyncStatus } from "../hooks/useExamAutosave2Tier";

export interface AutosaveStatusPillProps {
  status: AutosaveSyncStatus;
  lastSavedAt?: string;
}

export const AutosaveStatusPill: React.FC<AutosaveStatusPillProps> = ({
  status,
  lastSavedAt,
}) => {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
        status === "synced"
          ? "bg-[#ecfdf5] border-[#a7f3d0] text-[#15803d]"
          : status === "saving"
          ? "bg-[#eaf6fa] border-[#7fbbdd] text-[#006699]"
          : status === "offline_saved"
          ? "bg-[#fffbeb] border-[#fde68a] text-[#b45309]"
          : "bg-[#fff1f2] border-[#fecdd3] text-[#be123c]"
      }`}
    >
      {status === "synced" && (
        <>
          <CheckCircle2 className="w-3.5 h-3.5 text-[#15803d]" />
          <span>Đã lưu bài an toàn</span>
          {lastSavedAt && (
            <span className="opacity-70 text-[10px] font-mono">
              ({new Date(lastSavedAt).toLocaleTimeString()})
            </span>
          )}
        </>
      )}

      {status === "saving" && (
        <>
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#006699]" />
          <span>Đang đồng bộ máy chủ...</span>
        </>
      )}

      {status === "offline_saved" && (
        <>
          <HardDrive className="w-3.5 h-3.5 text-[#b45309]" />
          <span>Lưu bộ nhớ cục bộ (Mất mạng)</span>
        </>
      )}

      {status === "error" && (
        <>
          <AlertCircle className="w-3.5 h-3.5 text-[#be123c]" />
          <span>Chưa thể đồng bộ</span>
        </>
      )}
    </div>
  );
};
