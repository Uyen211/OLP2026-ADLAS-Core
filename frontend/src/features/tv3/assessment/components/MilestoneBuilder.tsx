// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { Plus, Trash2, AlertCircle } from "lucide-react";
import { EduButton, EduCard, EduInput } from "../../../../design-system";
import type { MilestoneCreateRequest } from "../../../../types/assessment";

export interface MilestoneBuilderProps {
  milestones: MilestoneCreateRequest[];
  onChange: (milestones: MilestoneCreateRequest[]) => void;
  disabled?: boolean;
}

export const MilestoneBuilder: React.FC<MilestoneBuilderProps> = ({
  milestones,
  onChange,
  disabled = false,
}) => {
  const totalWeight = milestones.reduce((sum, m) => sum + (Number(m.weight_percent) || 0), 0);
  const isValidWeight = Math.abs(totalWeight - 100) < 0.01;

  const handleAdd = () => {
    const nextOrder = milestones.length + 1;
    const remainingWeight = Math.max(0, 100 - totalWeight);
    onChange([
      ...milestones,
      {
        title: `Giai đoạn ${nextOrder}`,
        due_date: new Date(Date.now() + nextOrder * 7 * 86400000).toISOString().slice(0, 16),
        until_date: null,
        weight_percent: remainingWeight > 0 ? remainingWeight : 20,
        sort_order: nextOrder,
      },
    ]);
  };

  const handleRemove = (index: number) => {
    const updated = milestones.filter((_, idx) => idx !== index);
    onChange(updated);
  };

  const handleUpdate = (index: number, patch: Partial<MilestoneCreateRequest>) => {
    const updated = milestones.map((m, idx) => (idx === index ? { ...m, ...patch } : m));
    onChange(updated);
  };

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-[#f5fbfd] border border-[rgba(127,187,221,0.55)]">
        <div>
          <h4 className="text-sm font-bold text-[#0f2236]">
            Cơ cấu các mốc nộp bài (Milestones)
          </h4>
          <p className="text-xs text-[#4a5f75] mt-0.5">
            Tổng trọng số các giai đoạn bắt buộc đạt đúng 100%.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[#4a5f75]">Tổng:</span>
            <span
              className={`px-2.5 py-1 text-xs font-mono font-bold rounded-lg ${
                isValidWeight
                  ? "bg-[#ecfdf5] text-[#15803d] border border-[#15803d]/30"
                  : "bg-[#fffbeb] text-[#f58b05] border border-[#f58b05]/40"
              }`}
            >
              {totalWeight.toFixed(1)}% / 100%
            </span>
          </div>

          <EduButton
            variant="sky"
            size="sm"
            onClick={handleAdd}
            disabled={disabled}
            leftIcon={<Plus className="w-4 h-4" aria-hidden="true" />}
          >
            Thêm giai đoạn
          </EduButton>
        </div>
      </div>

      {!isValidWeight && (
        <div className="flex items-center gap-2 p-3 text-xs font-semibold text-[#f58b05] bg-[#fffbeb] rounded-xl border border-[#f58b05]/30">
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>
            {totalWeight < 100
              ? `Còn thiếu ${(100 - totalWeight).toFixed(1)}% nữa để đạt tổng 100%.`
              : `Tổng trọng số đang vượt quá ${(totalWeight - 100).toFixed(1)}%. Vui lòng điều chỉnh lại.`}
          </span>
        </div>
      )}

      {milestones.length === 0 ? (
        <div className="p-6 text-center text-xs text-[#4a5f75] bg-white rounded-xl border border-dashed border-[rgba(15,34,54,0.15)]">
          Chưa thiết lập mốc nộp bài phân kỳ. Bấm "Thêm giai đoạn" để tạo cột mốc đánh giá.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {milestones.map((m, idx) => (
            <EduCard
              key={idx}
              variant="surface"
              padding="sm"
              className="flex flex-col sm:flex-row sm:items-center gap-3 justify-between"
            >
              <div className="flex-1 grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
                <div className="sm:col-span-5">
                  <EduInput
                    label={`Giai đoạn ${idx + 1}`}
                    value={m.title}
                    onChange={(e) => handleUpdate(idx, { title: e.target.value })}
                    disabled={disabled}
                    placeholder="Tên giai đoạn nộp bài..."
                  />
                </div>

                <div className="sm:col-span-4">
                  <label className="text-xs font-semibold text-[#0f2236] block mb-1">
                    Hạn nộp (Due Date)
                  </label>
                  <input
                    type="datetime-local"
                    value={m.due_date ? m.due_date.slice(0, 16) : ""}
                    onChange={(e) => handleUpdate(idx, { due_date: e.target.value })}
                    disabled={disabled}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[rgba(15,34,54,0.18)] bg-white text-[#0f2236] outline-none focus:ring-2 focus:ring-[#7fbbdd]"
                  />
                </div>

                <div className="sm:col-span-3">
                  <EduInput
                    label="Trọng số (%)"
                    type="number"
                    min={1}
                    max={100}
                    step={1}
                    value={m.weight_percent}
                    onChange={(e) => handleUpdate(idx, { weight_percent: Number(e.target.value) || 0 })}
                    disabled={disabled}
                  />
                </div>
              </div>

              <div className="sm:pt-5 flex justify-end">
                <button
                  type="button"
                  onClick={() => handleRemove(idx)}
                  disabled={disabled}
                  aria-label={`Xóa giai đoạn ${idx + 1}`}
                  className="p-2 rounded-lg text-[#b91c1c] hover:bg-[#fef2f2] transition-colors disabled:opacity-50"
                >
                  <Trash2 className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </EduCard>
          ))}
        </div>
      )}
    </div>
  );
};
