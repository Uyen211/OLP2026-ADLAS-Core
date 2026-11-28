// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { ShieldAlert, Maximize, AlertTriangle, Wifi, WifiOff } from "lucide-react";

export interface StrictModeBannerProps {
  strikes: number;
  maxStrikes?: number;
  isFullscreen: boolean;
  onRequestFullscreen: () => void;
  isOnline?: boolean;
}

export const StrictModeBanner: React.FC<StrictModeBannerProps> = ({
  strikes,
  maxStrikes = 3,
  isFullscreen,
  onRequestFullscreen,
  isOnline = true,
}) => {
  const isDanger = strikes >= 2;

  return (
    <div
      className={`w-full px-4 py-2 text-xs font-semibold flex flex-wrap items-center justify-between gap-3 border-b transition-colors ${
        isDanger
          ? "bg-[#fff1f2] border-[#fecdd3] text-[#be123c]"
          : strikes > 0
          ? "bg-[#fffbeb] border-[#fde68a] text-[#b45309]"
          : "bg-[#0f2236] border-[#0f2236] text-white"
      }`}
    >
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-4 h-4 shrink-0" />
        <span>Chế độ Phòng thi Giám sát Nghiêm ngặt (Strict Proctored)</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Chỉ số vi phạm */}
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>
            Số lần cảnh báo: <strong className="font-mono">{strikes}</strong>/{maxStrikes}
          </span>
        </div>

        {/* Trạng thái Toàn màn hình */}
        {!isFullscreen && (
          <button
            type="button"
            onClick={onRequestFullscreen}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white text-[#0f2236] border border-black/10 font-bold hover:bg-[#eaf6fa]"
          >
            <Maximize className="w-3 h-3" />
            <span>Vào toàn màn hình</span>
          </button>
        )}

        {/* Trạng thái Kết nối mạng */}
        <div className="flex items-center gap-1 font-mono text-[11px]">
          {isOnline ? (
            <>
              <Wifi className="w-3.5 h-3.5 text-[#15803d]" />
              <span className="text-[#15803d]">Trực tuyến</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-[#be123c]" />
              <span className="text-[#be123c]">Mất kết nối</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
