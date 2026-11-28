// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { Plus, Trash2, AlertTriangle } from "lucide-react";
import { EduButton, EduCard } from "../../../../design-system";
import type {
  DrawRuleItem,
  QuestionFolderResponse,
  QuestionFolderStatsResponse,
} from "../../../../types/examination";

export interface DrawRulesBuilderProps {
  rules: DrawRuleItem[];
  folders: QuestionFolderResponse[];
  stats?: QuestionFolderStatsResponse;
  onChange: (rules: DrawRuleItem[]) => void;
  disabled?: boolean;
}

export const DrawRulesBuilder: React.FC<DrawRulesBuilderProps> = ({
  rules,
  folders,
  stats,
  onChange,
  disabled = false,
}) => {
  const handleAddRule = () => {
    const newRule: DrawRuleItem = {
      folder_id: folders[0]?.id || null,
      difficulty: null,
      count: 5,
      points_per_question: 1.0,
    };
    onChange([...rules, newRule]);
  };

  const handleUpdateRule = (index: number, field: keyof DrawRuleItem, value: any) => {
    const next = [...rules];
    next[index] = { ...next[index], [field]: value };
    onChange(next);
  };

  const handleDeleteRule = (index: number) => {
    onChange(rules.filter((_, i) => i !== index));
  };

  const totalQuestions = rules.reduce((sum, r) => sum + (Number(r.count) || 0), 0);
  const totalScore = rules.reduce(
    (sum, r) => sum + (Number(r.count) || 0) * (Number(r.points_per_question) || 0),
    0
  );

  return (
    <EduCard variant="surface" padding="md" className="space-y-4 border border-[rgba(15,34,54,0.12)]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[rgba(15,34,54,0.08)]">
        <div>
          <h4 className="text-sm font-bold text-[#0f2236]">Quy tắc Rút ngẫu nhiên từ Thư mục (Random Draw)</h4>
          <p className="text-xs text-[#4a5f75]">
            Mỗi đề thi của sinh viên sẽ tự động lấy ngẫu nhiên số lượng câu hỏi theo cấu hình dưới đây.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-semibold">
          <span className="px-2.5 py-1 rounded-lg bg-[#eaf6fa] text-[#006699]">
            Tổng số câu: <strong className="font-mono">{totalQuestions}</strong>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-[#ecfdf5] text-[#15803d]">
            Tổng điểm: <strong className="font-mono">{totalScore.toFixed(1)}</strong>
          </span>
        </div>
      </div>

      {rules.length === 0 ? (
        <div className="text-center py-6 text-xs text-[#4a5f75]">
          Chưa thiết lập quy tắc rút ngẫu nhiên nào. Đề thi sẽ lấy câu hỏi cố định từ danh sách.
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule, idx) => {
            const availableCount = rule.folder_id
              ? stats?.by_folder?.[rule.folder_id] || 0
              : stats?.total_questions || 0;
            const isDeficient = rule.count > availableCount;

            return (
              <div
                key={idx}
                className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-center gap-3 transition-colors ${
                  isDeficient ? "bg-[#fff1f2] border-[#fecdd3]" : "bg-[#f5fbfd] border-[rgba(15,34,54,0.08)]"
                }`}
              >
                <div className="flex-1">
                  <label className="block text-[11px] font-semibold text-[#4a5f75] mb-1">
                    Thư mục nguồn
                  </label>
                  <select
                    disabled={disabled}
                    value={rule.folder_id || ""}
                    onChange={(e) => handleUpdateRule(idx, "folder_id", e.target.value || null)}
                    className="w-full text-xs rounded-lg border border-[rgba(15,34,54,0.15)] p-1.5 bg-white text-[#0f2236]"
                  >
                    <option value="">(Tất cả thư mục)</option>
                    {folders.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.folder_name} (Hiện có: {stats?.by_folder?.[f.id] || 0} câu)
                      </option>
                    ))}
                  </select>
                </div>

                <div className="w-32">
                  <label className="block text-[11px] font-semibold text-[#4a5f75] mb-1">
                    Độ khó
                  </label>
                  <select
                    disabled={disabled}
                    value={rule.difficulty || ""}
                    onChange={(e) => handleUpdateRule(idx, "difficulty", e.target.value || null)}
                    className="w-full text-xs rounded-lg border border-[rgba(15,34,54,0.15)] p-1.5 bg-white text-[#0f2236]"
                  >
                    <option value="">Tất cả độ khó</option>
                    <option value="easy">Dễ</option>
                    <option value="medium">Trung bình</option>
                    <option value="hard">Khó</option>
                  </select>
                </div>

                <div className="w-24">
                  <label className="block text-[11px] font-semibold text-[#4a5f75] mb-1">
                    Số câu lấy
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    disabled={disabled}
                    value={rule.count}
                    onChange={(e) => handleUpdateRule(idx, "count", Number(e.target.value))}
                    className="w-full text-xs rounded-lg border border-[rgba(15,34,54,0.15)] p-1.5 bg-white font-mono text-[#0f2236]"
                  />
                </div>

                <div className="w-24">
                  <label className="block text-[11px] font-semibold text-[#4a5f75] mb-1">
                    Điểm / câu
                  </label>
                  <input
                    type="number"
                    step="0.25"
                    min="0.25"
                    disabled={disabled}
                    value={rule.points_per_question}
                    onChange={(e) => handleUpdateRule(idx, "points_per_question", Number(e.target.value))}
                    className="w-full text-xs rounded-lg border border-[rgba(15,34,54,0.15)] p-1.5 bg-white font-mono text-[#0f2236]"
                  />
                </div>

                {!disabled && (
                  <button
                    type="button"
                    onClick={() => handleDeleteRule(idx)}
                    className="p-1.5 text-[#b91c1c] hover:bg-rose-50 rounded mt-4 sm:mt-0"
                    title="Xóa quy tắc này"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}

                {isDeficient && (
                  <div className="sm:hidden text-xs text-[#be123c] flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Thư mục chỉ có {availableCount} câu, không đủ rút {rule.count} câu!</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!disabled && (
        <EduButton
          type="button"
          variant="secondary"
          size="sm"
          onClick={handleAddRule}
        >
          <Plus className="w-3.5 h-3.5 mr-1" />
          <span>Thêm quy tắc rút câu hỏi</span>
        </EduButton>
      )}
    </EduCard>
  );
};
