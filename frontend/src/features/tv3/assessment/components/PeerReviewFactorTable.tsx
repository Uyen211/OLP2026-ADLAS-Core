// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { EduBadge, EduCard } from "../../../../design-system";
import type { PeerReviewSummaryResponse } from "../../../../types/assessment";

export interface PeerReviewFactorTableProps {
  summary: PeerReviewSummaryResponse;
  rawGroupGrade?: number;
  isInstructor?: boolean;
  onOverrideFactor?: (studentId: string, newFactor: number) => void;
}

export const PeerReviewFactorTable: React.FC<PeerReviewFactorTableProps> = ({
  summary,
  rawGroupGrade = 8.5,
  isInstructor = false,
  onOverrideFactor,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [overrideValue, setOverrideValue] = useState<string>("");

  const summaries = summary.summaries || [];
  const groupAvg = summaries[0]?.group_average_score ?? 0;

  const handleStartEdit = (studentId: string, currentFactor: number) => {
    if (!isInstructor) return;
    setEditingId(studentId);
    setOverrideValue(currentFactor.toString());
  };

  const handleSaveOverride = (studentId: string) => {
    const val = parseFloat(overrideValue);
    if (!isNaN(val) && val >= 0.5 && val <= 1.2) {
      if (onOverrideFactor) {
        onOverrideFactor(studentId, val);
      }
    }
    setEditingId(null);
  };

  return (
    <EduCard variant="surface" padding="none" className="overflow-hidden border border-[rgba(15,34,54,0.12)]">
      <div className="p-4 bg-[#f5fbfd] border-b border-[rgba(15,34,54,0.08)] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-[#0f2236]">
            Bảng Tổng hợp Hệ số Đóng góp Fi
          </h3>
          <p className="text-xs text-[#4a5f75] mt-0.5">
            Điểm cá nhân = Điểm nhóm x Hệ số Fi (giới hạn trong biên độ chuẩn [0.50, 1.20])
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs font-semibold text-[#0f2236]">
          <div className="px-3 py-1.5 rounded-lg bg-white border border-[rgba(15,34,54,0.12)]">
            <span className="text-[#4a5f75] mr-1.5">Điểm nhóm ban đầu:</span>
            <span className="font-mono text-[#006699] font-bold">{rawGroupGrade.toFixed(1)}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-white border border-[rgba(15,34,54,0.12)]">
            <span className="text-[#4a5f75] mr-1.5">TB nhóm (S̄):</span>
            <span className="font-mono text-[#006699] font-bold">
              {groupAvg > 0 ? groupAvg.toFixed(1) : "Chưa có"}
            </span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[rgba(15,34,54,0.08)] bg-[#eaf6fa]/40 text-[11px] font-bold uppercase tracking-wider text-[#4a5f75]">
              <th className="py-3 px-4">Thành viên</th>
              <th className="py-3 px-3 text-right">Điểm TB nhận (Si)</th>
              <th className="py-3 px-3 text-center">Hệ số Fi</th>
              <th className="py-3 px-3 text-right">Điểm cá nhân (Gi)</th>
              {isInstructor && <th className="py-3 px-4 text-center">Thao tác</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-[rgba(15,34,54,0.06)] text-sm">
            {summaries.map((m) => {
              const fi = m.factor_f ?? 1.0;
              const adjustedScore = m.adjusted_grade ?? Math.min(10, Math.round(rawGroupGrade * fi * 100) / 100);

              return (
                <tr key={m.student_id} className="hover:bg-[#f5fbfd] transition-colors">
                  <td className="py-3 px-4">
                    <span className="font-semibold text-[#0f2236] block">
                      {m.student_name || "Sinh viên"}
                    </span>
                    <span className="text-xs text-[#4a5f75] font-mono">
                      {m.student_email || m.student_id}
                    </span>
                  </td>

                  <td className="py-3 px-3 text-right font-mono font-semibold text-[#0f2236]">
                    {m.average_score_received != null ? m.average_score_received.toFixed(1) : "—"}
                  </td>

                  <td className="py-3 px-3 text-center">
                    {editingId === m.student_id ? (
                      <div className="flex items-center justify-center gap-1">
                        <input
                          type="number"
                          step="0.05"
                          min="0.5"
                          max="1.2"
                          value={overrideValue}
                          onChange={(e) => setOverrideValue(e.target.value)}
                          className="w-16 px-1.5 py-0.5 text-xs text-center border rounded font-mono"
                        />
                        <button
                          type="button"
                          onClick={() => handleSaveOverride(m.student_id)}
                          className="px-2 py-0.5 bg-[#006699] text-white text-xs rounded"
                        >
                          Lưu
                        </button>
                      </div>
                    ) : (
                      <div
                        className="inline-flex items-center gap-1 cursor-pointer"
                        onClick={() => handleStartEdit(m.student_id, fi)}
                        title={isInstructor ? "Bấm để điều chỉnh hệ số thủ công" : undefined}
                      >
                        <EduBadge
                          variant={fi > 1.02 ? "correct" : fi < 0.98 ? "incorrect" : "neutral"}
                          label={fi.toFixed(2)}
                        />
                      </div>
                    )}
                  </td>

                  <td className="py-3 px-3 text-right font-mono font-bold text-base text-[#006699]">
                    {adjustedScore.toFixed(2)}
                  </td>

                  {isInstructor && (
                    <td className="py-3 px-4 text-center">
                      <button
                        type="button"
                        onClick={() => handleStartEdit(m.student_id, fi)}
                        className="text-xs text-[#006699] hover:underline font-semibold"
                      >
                        {editingId === m.student_id ? "Hủy" : "Điều chỉnh"}
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </EduCard>
  );
};

