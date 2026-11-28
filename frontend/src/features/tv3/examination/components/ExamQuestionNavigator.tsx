// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { Flag } from "lucide-react";
import { EduCard } from "../../../../design-system";

export interface ExamQuestionNavigatorProps {
  totalQuestions: number;
  currentIndex: number;
  answeredQuestionIds: string[];
  flaggedQuestionIds: string[];
  questionIds: string[];
  onSelectQuestion: (index: number) => void;
}

export const ExamQuestionNavigator: React.FC<ExamQuestionNavigatorProps> = ({
  totalQuestions,
  currentIndex,
  answeredQuestionIds,
  flaggedQuestionIds,
  questionIds,
  onSelectQuestion,
}) => {
  return (
    <EduCard variant="surface" padding="md" className="space-y-3 border border-[rgba(15,34,54,0.12)]">
      <div className="flex items-center justify-between pb-2 border-b border-[rgba(15,34,54,0.08)]">
        <h4 className="text-xs font-bold uppercase tracking-wider text-[#0f2236]">
          Danh sách câu hỏi
        </h4>
        <span className="text-xs font-mono text-[#4a5f75]">
          {answeredQuestionIds.length}/{totalQuestions}
        </span>
      </div>

      <div className="grid grid-cols-5 gap-2 max-h-[300px] overflow-y-auto pr-1">
        {Array.from({ length: totalQuestions }).map((_, idx) => {
          const qId = questionIds[idx];
          const isAnswered = answeredQuestionIds.includes(qId);
          const isFlagged = flaggedQuestionIds.includes(qId);
          const isCurrent = idx === currentIndex;

          let btnClass = "bg-white text-[#0f2236] border-[rgba(15,34,54,0.15)]";
          if (isCurrent) {
            btnClass = "ring-2 ring-[#006699] border-[#006699] font-bold";
          }
          if (isAnswered) {
            btnClass += " bg-[#eaf6fa] text-[#006699] border-[#7fbbdd]";
          }

          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectQuestion(idx)}
              className={`relative h-9 rounded-xl border text-xs font-mono flex items-center justify-center transition-all hover:scale-105 ${btnClass}`}
            >
              <span>{idx + 1}</span>
              {isFlagged && (
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#f58b05] text-white flex items-center justify-center">
                  <Flag className="w-2 h-2" fill="currentColor" />
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Legend chú thích */}
      <div className="pt-2 border-t border-[rgba(15,34,54,0.08)] flex flex-wrap gap-2 text-[10px] text-[#4a5f75]">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-white border border-[rgba(15,34,54,0.2)]" />
          <span>Chưa làm</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-[#eaf6fa] border border-[#7fbbdd]" />
          <span>Đã làm</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-[#f58b05]" />
          <span>Đã gắn cờ</span>
        </div>
      </div>
    </EduCard>
  );
};
