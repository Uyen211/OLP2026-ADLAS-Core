/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import { BarChart3, X } from "lucide-react";
import type { GradeDistributionBucket } from "../../../../types/gradebook";
import { MmButton } from "../../components/MmButton";

interface GradeDistributionModalProps {
  open: boolean;
  buckets: GradeDistributionBucket[];
  passRatePct: number;
  failRatePct: number;
  classAverage10?: number | null;
  onClose: () => void;
}

export const GradeDistributionModal: React.FC<GradeDistributionModalProps> = ({
  open,
  buckets,
  passRatePct,
  failRatePct,
  classAverage10,
  onClose,
}) => {
  if (!open) return null;

  const maxCount = Math.max(1, ...buckets.map((b) => b.count));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-mm-border bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between border-b border-mm-divider pb-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-mm-blue-primary" />
            <div>
              <h2 className="font-mm-display text-lg font-semibold text-mm-heading">
                Biểu đồ Phổ điểm Toàn lớp (TT 08/2021)
              </h2>
              <p className="text-xs text-mm-text-secondary">
                Phân bố xếp loại tín chỉ và tỷ lệ qua môn của lớp học phần
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-mm-text-secondary hover:bg-mm-divider"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-center">
            <p className="text-xs text-emerald-700">Tỷ lệ Đạt môn</p>
            <p className="mt-1 font-mm-mono text-xl font-bold text-emerald-800">{passRatePct}%</p>
          </div>
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-center">
            <p className="text-xs text-rose-700">Tỷ lệ Rớt môn</p>
            <p className="mt-1 font-mm-mono text-xl font-bold text-rose-800">{failRatePct}%</p>
          </div>
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-3 text-center">
            <p className="text-xs text-blue-700">Điểm TB Lớp (Hệ 10)</p>
            <p className="mt-1 font-mm-mono text-xl font-bold text-blue-800">
              {classAverage10 !== null && classAverage10 !== undefined ? classAverage10 : "--"}
            </p>
          </div>
        </div>

        <div className="mt-6 space-y-3">
          {buckets.map((bucket) => {
            const widthPct = Math.round((bucket.count / maxCount) * 100);
            const isFail = bucket.label === "F";
            return (
              <div key={bucket.label} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-mm-heading">
                    {bucket.label}{" "}
                    <span className="font-normal text-mm-text-muted">({bucket.range_hint})</span>
                  </span>
                  <span className="font-mm-mono text-mm-text-secondary">
                    {bucket.count} SV ({bucket.percentage}%)
                  </span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all ${
                      isFail ? "bg-rose-500" : "bg-blue-600"
                    }`}
                    style={{ width: `${bucket.count > 0 ? Math.max(4, widthPct) : 0}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-6 flex justify-end border-t border-mm-divider pt-4">
          <MmButton variant="secondary" onClick={onClose}>
            <span>Đóng</span>
          </MmButton>
        </div>
      </div>
    </div>
  );
};
