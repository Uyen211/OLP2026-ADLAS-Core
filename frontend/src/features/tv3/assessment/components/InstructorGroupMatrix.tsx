// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { Shuffle } from "lucide-react";
import { EduButton, EduCard, EduConfirmDialog } from "../../../../design-system";
import type { StudentGroupResponse } from "../../../../types/assessment";
import { assessmentService } from "../../../../services/assessmentService";

export interface InstructorGroupMatrixProps {
  assignmentId: string;
  groups: StudentGroupResponse[];
  onRefresh?: () => void;
}

export const InstructorGroupMatrix: React.FC<InstructorGroupMatrixProps> = ({
  assignmentId,
  groups,
  onRefresh,
}) => {
  const [isAutoAssigning, setIsAutoAssigning] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleAutoAssign = async () => {
    setIsAutoAssigning(true);
    try {
      await assessmentService.autoAssignGroups(assignmentId);
      setConfirmOpen(false);
      if (onRefresh) onRefresh();
    } catch (err: any) {
      alert("Ghép nhóm tự động không thành công: " + (err?.message || "Lỗi server"));
    } finally {
      setIsAutoAssigning(false);
    }
  };

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-[#0f2236]">
            Danh sách Nhóm Đồ án ({groups.length})
          </h3>
          <p className="text-xs text-[#4a5f75] mt-0.5">
            Giảng viên theo dõi danh sách nhóm, thành viên và đề tài đã chọn.
          </p>
        </div>

        <EduButton
          variant="secondary"
          size="sm"
          onClick={() => setConfirmOpen(true)}
          leftIcon={<Shuffle className="w-4 h-4" aria-hidden="true" />}
        >
          Ghép nhóm tự động
        </EduButton>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {groups.map((g) => (
          <EduCard key={g.id} variant="surface" padding="sm" className="flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#f5fbfd] border border-[rgba(15,34,54,0.1)] text-[#0f2236]">
                  {g.join_code}
                </span>
                <span className="text-xs text-[#4a5f75]">
                  {g.members?.length || 0} thành viên
                </span>
              </div>

              <h4 className="text-sm font-bold text-[#0f2236] truncate">{g.group_name}</h4>
              <p className="text-xs text-[#4a5f75] mt-1 truncate">
                Đề tài: {g.topic_title || "Chưa chọn đề tài"}
              </p>
            </div>

            <div className="mt-3 pt-2.5 border-t border-[rgba(15,34,54,0.06)] flex items-center justify-between text-xs text-[#4a5f75]">
              <span>Trưởng nhóm:</span>
              <span className="font-semibold text-[#0f2236]">
                {g.members?.find((m) => m.role === "LEADER")?.student_name || "Chưa xác định"}
              </span>
            </div>
          </EduCard>
        ))}
      </div>

      <EduConfirmDialog
        isOpen={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleAutoAssign}
        title="Xác nhận Ghép nhóm tự động"
        message="Hệ thống sẽ tự động ghép các sinh viên chưa có nhóm vào các nhóm còn thiếu người và tạo các nhóm mới hợp lệ, đồng thời khóa danh sách nhóm. Thao tác này không thể hoàn tác."
        confirmLabel="Tiến hành ghép nhóm"
        variant="amber"
        isLoading={isAutoAssigning}
      />
    </div>
  );
};
