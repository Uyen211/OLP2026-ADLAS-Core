/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { clsx } from "clsx";
import { ClipboardList, Edit3, Lock, Target } from "lucide-react";
import type {
  MasteryLevelCode,
  MasteryLevelItem,
  RubricResponse,
} from "../../../../types/assessment";
import type { LOResponse } from "../../../../types/course";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";

export interface RubricPreviewCardProps {
  rubric: RubricResponse | null;
  loading?: boolean;
  learningObjectives?: LOResponse[];
  isInstructor?: boolean;
  editHref?: string;
}

const MASTERY_COLUMNS: Array<{
  code: MasteryLevelCode;
  label: string;
  badgeClass: string;
}> = [
  {
    code: "EXCELLENT",
    label: "Xuất sắc",
    badgeClass: "bg-mm-success-bg text-mm-success",
  },
  {
    code: "GOOD",
    label: "Khá / Giỏi",
    badgeClass: "bg-mm-blue-light/35 text-mm-blue-deep",
  },
  {
    code: "PROFICIENT",
    label: "Đạt chuẩn cơ bản",
    badgeClass: "bg-mm-warning-bg text-mm-warning",
  },
  {
    code: "INSUFFICIENT",
    label: "Chưa đạt",
    badgeClass: "bg-mm-danger-bg text-mm-danger",
  },
];

function findLevel(
  levels: MasteryLevelItem[],
  code: MasteryLevelCode
): MasteryLevelItem | undefined {
  return levels.find((item) => item.level === code);
}

export const RubricPreviewCard: React.FC<RubricPreviewCardProps> = ({
  rubric,
  loading = false,
  learningObjectives = [],
  isInstructor = false,
  editHref,
}) => {
  const loById = useMemo(() => {
    const map = new Map<string, LOResponse>();
    for (const lo of learningObjectives) {
      map.set(lo.id, lo);
    }
    return map;
  }, [learningObjectives]);

  if (loading) {
    return (
      <MmCard variant="standard" className="space-y-3">
        <div className="h-6 w-56 animate-pulse rounded-mm-btn bg-mm-divider" />
        <div className="h-36 animate-pulse rounded-mm-panel bg-mm-divider/50" />
      </MmCard>
    );
  }

  if (!rubric || !rubric.exists || rubric.criteria.length === 0) {
    return (
      <MmCard variant="standard" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-mm-blue-hover" />
            <h2 className="font-mm-display text-lg font-semibold text-mm-heading">
              Bảng tiêu chí chấm điểm (Rubric)
            </h2>
          </div>
          {isInstructor && editHref && (
            <Link to={editHref}>
              <MmButton variant="brand" size="sm">
                <Edit3 className="h-4 w-4" />
                <span>Thiết kế Rubric</span>
              </MmButton>
            </Link>
          )}
        </div>
        <p className="font-mm-ui text-sm text-mm-text-secondary">
          {isInstructor
            ? "Bài tập này chưa có bảng Rubric. Hãy thiết kế bảng tiêu chí 4 mức độ (tổng 10.0 điểm) để sinh viên nắm rõ yêu cầu đánh giá."
            : "Giảng viên chưa công bố bảng tiêu chí chấm điểm chi tiết cho bài tập này."}
        </p>
      </MmCard>
    );
  }

  return (
    <MmCard variant="standard" padding="none" className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-mm-divider px-6 py-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <ClipboardList className="h-5 w-5 text-mm-blue-hover" />
            <h2 className="font-mm-display text-lg font-semibold text-mm-heading">
              {rubric.title || "Bảng tiêu chí chấm điểm (Rubric)"}
            </h2>
            <span className="rounded-full bg-mm-btn-secondary px-2.5 py-0.5 font-mm-data text-xs font-medium text-mm-text-secondary">
              v{rubric.version}
            </span>
            <span className="rounded-full bg-mm-blue-light/35 px-2.5 py-0.5 font-mm-data text-xs font-medium text-mm-blue-deep">
              Tổng {Number(rubric.total_points).toFixed(1)} điểm
            </span>
            {rubric.is_frozen && (
              <span className="inline-flex items-center gap-1 rounded-full bg-mm-warning-bg px-2.5 py-0.5 font-mm-ui text-xs font-medium text-mm-warning">
                <Lock className="h-3 w-3" />
                <span>Đã đóng băng ({rubric.submission_count} bài nộp)</span>
              </span>
            )}
          </div>
          <p className="font-mm-ui text-xs text-mm-text-secondary">
            Thang đánh giá 4 mức độ năng lực giúp sinh viên đối chiếu tiêu chuẩn chấm điểm trước khi nộp bài
          </p>
        </div>

        {isInstructor && editHref && (
          <Link to={editHref}>
            <MmButton variant="secondary" size="sm">
              <Edit3 className="h-4 w-4" />
              <span>{rubric.is_frozen ? "Xem chi tiết Rubric" : "Chỉnh sửa Rubric"}</span>
            </MmButton>
          </Link>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[780px] border-collapse text-left">
          <thead>
            <tr className="border-b border-mm-divider bg-mm-divider/35 font-mm-ui text-xs font-medium text-mm-text-secondary">
              <th className="w-[24%] px-5 py-3.5">Tiêu chí đánh giá</th>
              {MASTERY_COLUMNS.map((col) => (
                <th key={col.code} className="w-[19%] px-4 py-3.5">
                  <span
                    className={clsx(
                      "inline-flex rounded-full px-2.5 py-0.5 font-mm-ui text-xs font-medium",
                      col.badgeClass
                    )}
                  >
                    {col.label}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-mm-divider font-mm-ui text-xs">
            {rubric.criteria.map((criterion, idx) => {
              const linkedLo = criterion.lo_id
                ? loById.get(criterion.lo_id)
                : undefined;

              return (
                <tr key={criterion.id} className="align-top hover:bg-mm-divider/15">
                  <td className="px-5 py-4">
                    <div className="space-y-1.5">
                      <p className="font-mm-mid text-sm font-medium text-mm-heading">
                        {idx + 1}. {criterion.title}
                      </p>
                      {criterion.description && (
                        <p className="text-xs leading-relaxed text-mm-text-secondary">
                          {criterion.description}
                        </p>
                      )}
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="rounded-full bg-mm-btn-secondary px-2 py-0.5 font-mm-data text-[11px] font-medium text-mm-heading">
                          {Number(criterion.max_points).toFixed(1)} điểm
                        </span>
                        {linkedLo && (
                          <span
                            title={linkedLo.description}
                            className="inline-flex items-center gap-1 rounded-full bg-mm-blue-light/30 px-2 py-0.5 font-mm-mono text-[11px] font-medium text-mm-blue-deep"
                          >
                            <Target className="h-3 w-3" />
                            <span>{linkedLo.code}</span>
                          </span>
                        )}
                        {criterion.competency_code && (
                          <span className="rounded-full bg-mm-divider px-2 py-0.5 font-mm-mono text-[11px] font-medium text-mm-text-secondary">
                            {criterion.competency_code}
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  {MASTERY_COLUMNS.map((col) => {
                    const level = findLevel(criterion.rating_levels, col.code);
                    return (
                      <td key={col.code} className="px-4 py-4">
                        {level ? (
                          <div className="space-y-1">
                            <span className="inline-block font-mm-data text-xs font-semibold text-mm-heading">
                              {Number(level.points).toFixed(1)} điểm
                            </span>
                            <p className="leading-relaxed text-mm-text-secondary">
                              {level.description || "Chưa có mô tả chi tiết."}
                            </p>
                          </div>
                        ) : (
                          <span className="text-mm-text-muted">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </MmCard>
  );
};
