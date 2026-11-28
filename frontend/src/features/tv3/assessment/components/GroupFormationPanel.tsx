// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { Copy, Check, UserPlus, KeyRound, ArrowRight } from "lucide-react";
import { EduButton, EduCard, EduInput } from "../../../../design-system";
import type { StudentGroupResponse } from "../../../../types/assessment";
import { assessmentService } from "../../../../services/assessmentService";

export interface GroupFormationPanelProps {
  assignmentId: string;
  currentGroup?: StudentGroupResponse | null;
  userId?: string;
  onGroupUpdated?: () => void;
}

export const GroupFormationPanel: React.FC<GroupFormationPanelProps> = ({
  assignmentId,
  currentGroup,
  userId,
  onGroupUpdated,
}) => {
  const [groupName, setGroupName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!groupName.trim()) return;

    setIsLoading(true);
    setErrorMsg(null);
    try {
      await assessmentService.createGroup(assignmentId, {
        group_name: groupName.trim(),
      });
      setGroupName("");
      if (onGroupUpdated) onGroupUpdated();
    } catch (err: any) {
      setErrorMsg(err?.message || "Không thể tạo nhóm. Vui lòng thử lại.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoinByCode = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = joinCode.trim().toUpperCase();
    if (!cleanCode || cleanCode.length !== 6) {
      setErrorMsg("Mã mời nhóm gồm đúng 6 ký tự.");
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    try {
      await assessmentService.joinGroupByCode(assignmentId, cleanCode);
      setJoinCode("");
      if (onGroupUpdated) onGroupUpdated();
    } catch (err: any) {
      setErrorMsg(err?.message || "Không thể gia nhập nhóm bằng mã này.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (currentGroup) {
    const isLeader = currentGroup.leader_student_id === userId;

    return (
      <EduCard variant="surface" padding="lg" className="w-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[rgba(15,34,54,0.08)]">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#4a5f75]">
                Nhóm của bạn
              </span>
              {isLeader && (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-[rgba(245,139,5,0.12)] text-[#F58B05]">
                  Trưởng nhóm
                </span>
              )}
              {currentGroup.is_finalized && (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-[#ecfdf5] text-[#15803d]">
                  Đã chốt danh sách
                </span>
              )}
            </div>
            <h3 className="text-xl font-bold text-[#0f2236] mt-0.5">
              {currentGroup.group_name}
            </h3>
          </div>

          <div className="flex items-center gap-3 bg-[#f5fbfd] p-2.5 rounded-xl border border-[rgba(127,187,221,0.55)]">
            <div className="text-left">
              <span className="text-[10px] font-semibold text-[#4a5f75] block uppercase">
                Mã mời nhóm
              </span>
              <span className="text-base font-mono font-bold tracking-widest text-[#0f2236]">
                {currentGroup.join_code}
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleCopyCode(currentGroup.join_code)}
              aria-label="Sao chép mã mời"
              className="p-2 rounded-lg bg-white border border-[rgba(15,34,54,0.12)] text-[#0f2236] hover:bg-[#eaf6fa] transition-colors"
            >
              {copied ? (
                <Check className="w-4 h-4 text-[#15803d]" aria-hidden="true" />
              ) : (
                <Copy className="w-4 h-4 text-[#4a5f75]" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        <div className="mt-5">
          <h4 className="text-sm font-bold text-[#0f2236] mb-3">
            Thành viên nhóm ({currentGroup.members?.length || 0})
          </h4>
          <div className="flex flex-col gap-2">
            {currentGroup.members?.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between p-3 rounded-xl bg-[#f5fbfd] border border-[rgba(15,34,54,0.06)]"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#c4e9f2] text-[#0f2236] font-bold text-xs flex items-center justify-center">
                    {(m.student_name || "S").charAt(0)}
                  </div>
                  <div>
                    <span className="text-sm font-semibold text-[#0f2236] block">
                      {m.student_name || "Sinh viên"}
                    </span>
                    <span className="text-xs text-[#4a5f75]">
                      {m.student_email || ""}
                    </span>
                  </div>
                </div>

                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    m.role === "LEADER"
                      ? "bg-[#fff8e1] text-[#7a4100] border border-[#ffc22f]/50"
                      : "bg-white text-[#4a5f75] border border-[rgba(15,34,54,0.1)]"
                  }`}
                >
                  {m.role === "LEADER" ? "Nhóm trưởng" : "Thành viên"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </EduCard>
    );
  }

  return (
    <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Create Group Box */}
      <EduCard variant="surface" padding="md" className="flex flex-col justify-between">
        <div>
          <div className="w-10 h-10 rounded-xl bg-[#c4e9f2] flex items-center justify-center text-[#0f2236] mb-3">
            <UserPlus className="w-5 h-5" aria-hidden="true" />
          </div>
          <h3 className="text-base font-bold text-[#0f2236]">Tạo nhóm mới</h3>
          <p className="text-xs text-[#4a5f75] mt-1">
            Khởi tạo nhóm đồ án, bạn sẽ trở thành nhóm trưởng và nhận mã mời 6 ký tự để chia sẻ.
          </p>

          <form onSubmit={handleCreateGroup} className="mt-4 flex flex-col gap-3">
            <EduInput
              placeholder="Nhập tên nhóm (VD: Nhóm 1 - AI Lab)..."
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              disabled={isLoading}
            />
            <EduButton type="submit" variant="primary" size="md" isLoading={isLoading}>
              Khởi tạo nhóm
            </EduButton>
          </form>
        </div>
      </EduCard>

      {/* Join Group By Code Box */}
      <EduCard variant="tint" padding="md" className="flex flex-col justify-between">
        <div>
          <div className="w-10 h-10 rounded-xl bg-[#f58b05]/20 flex items-center justify-center text-[#f58b05] mb-3">
            <KeyRound className="w-5 h-5" aria-hidden="true" />
          </div>
          <h3 className="text-base font-bold text-[#0f2236]">Gia nhập bằng mã mời</h3>
          <p className="text-xs text-[#4a5f75] mt-1">
            Nhập mã mời 6 ký tự do nhóm trưởng cung cấp để tham gia nhóm đồ án.
          </p>

          <form onSubmit={handleJoinByCode} className="mt-4 flex flex-col gap-3">
            <input
              type="text"
              maxLength={6}
              placeholder="VD: H8K92X"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
              disabled={isLoading}
              className="w-full px-3.5 py-2.5 text-center text-sm font-bold font-mono tracking-widest uppercase rounded-xl border border-[rgba(15,34,54,0.18)] bg-white text-[#0f2236] outline-none focus:ring-2 focus:ring-[#7fbbdd]"
            />
            <EduButton
              type="submit"
              variant="amber"
              size="md"
              isLoading={isLoading}
              rightIcon={<ArrowRight className="w-4 h-4" aria-hidden="true" />}
            >
              Gia nhập nhóm
            </EduButton>
          </form>
        </div>
      </EduCard>

      {errorMsg && (
        <div className="md:col-span-2 p-3 text-xs font-semibold text-[#b91c1c] bg-[#fef2f2] rounded-xl border border-[#b91c1c]/20">
          {errorMsg}
        </div>
      )}
    </div>
  );
};
