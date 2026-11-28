// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { Clock, ShieldAlert } from "lucide-react";
import { EduBadge, EduDrawer } from "../../../../design-system";
import type { StrictViolationEvent } from "../hooks/useStrictExamGuard";

export interface AlertTimelineDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  violations: StrictViolationEvent[];
  studentName?: string;
}

export const AlertTimelineDrawer: React.FC<AlertTimelineDrawerProps> = ({
  isOpen,
  onClose,
  violations,
  studentName,
}) => {
  return (
    <EduDrawer
      isOpen={isOpen}
      onClose={onClose}
      title="Nhật ký Giám sát & Cảnh báo Vi phạm"
      width="md"
    >
      <div className="space-y-4">
        {studentName && (
          <div className="text-xs font-semibold text-[#4a5f75] pb-2 border-b border-[rgba(15,34,54,0.08)]">
            Thí sinh: <strong className="text-[#0f2236]">{studentName}</strong>
          </div>
        )}

        {violations.length === 0 ? (
          <div className="text-center py-12 text-xs text-[#4a5f75]">
            <ShieldAlert className="w-8 h-8 text-[#15803d] mx-auto mb-2 opacity-50" />
            <p>Không ghi nhận bất kỳ cảnh báo vi phạm nào trong suốt ca thi.</p>
          </div>
        ) : (
          <div className="space-y-3 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[rgba(15,34,54,0.1)]">
            {violations.map((v) => (
              <div key={v.id} className="relative pl-8 space-y-1">
                {/* Timeline dot */}
                <div
                  className={`absolute left-2 top-1.5 w-3.5 h-3.5 rounded-full border-2 border-white -translate-x-1/2 ${
                    v.strikeNumber >= 3
                      ? "bg-[#be123c]"
                      : v.strikeNumber === 2
                      ? "bg-[#f58b05]"
                      : "bg-[#7fbbdd]"
                  }`}
                />

                <div className="p-3 rounded-xl border border-[rgba(15,34,54,0.1)] bg-[#f5fbfd] space-y-1">
                  <div className="flex items-center justify-between">
                    <EduBadge
                      variant={
                        v.strikeNumber >= 3
                          ? "incorrect"
                          : v.strikeNumber === 2
                          ? "hint"
                          : "sky"
                      }
                      label={`Lần ${v.strikeNumber}: ${v.type}`}
                    />
                    <div className="flex items-center gap-1 text-[11px] font-mono text-[#4a5f75]">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(v.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>

                  <p className="text-xs font-medium text-[#0f2236] pt-1">
                    {v.message}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </EduDrawer>
  );
};
