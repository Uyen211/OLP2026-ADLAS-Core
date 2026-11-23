/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { AlertCircle, GripVertical, Save, Shuffle, Users } from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import type {
  GroupItemResponse,
  GroupMemberResponse,
  GroupingMode,
  GroupSetResponse,
} from "../../../../types/course";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface GroupPartitionModalProps {
  open: boolean;
  courseId: string;
  onClose: () => void;
  onSaved: (groupSet: GroupSetResponse) => void;
}

const MODE_OPTIONS: Array<{ value: GroupingMode; label: string }> = [
  { value: "RANDOM", label: "Chia ngẫu nhiên đồng đều" },
  { value: "SELF_SIGNUP", label: "Tạo nhóm trống để sinh viên tự chọn" },
  { value: "MANUAL", label: "Thủ công (tạo khung nhóm để kéo thả)" },
];

export const GroupPartitionModal: React.FC<GroupPartitionModalProps> = ({
  open,
  courseId,
  onClose,
  onSaved,
}) => {
  const [groupSetName, setGroupSetName] = useState("Nhóm Đồ án cuối kỳ");
  const [mode, setMode] = useState<GroupingMode>("RANDOM");
  const [groupSize, setGroupSize] = useState(4);
  const [draftGroups, setDraftGroups] = useState<GroupItemResponse[] | null>(null);

  const [previewLoading, setPreviewLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragPayload, setDragPayload] = useState<{
    fromGroupIdx: number;
    member: GroupMemberResponse;
  } | null>(null);

  const reset = () => {
    setDraftGroups(null);
    setError(null);
    setDragPayload(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleGeneratePreview = async (event: React.FormEvent) => {
    event.preventDefault();
    if (groupSetName.trim().length < 2) {
      setError("Tên bộ nhóm phải có ít nhất 2 ký tự.");
      return;
    }
    if (groupSize < 2 || groupSize > 10) {
      setError("Số sinh viên mỗi nhóm phải từ 2 đến 10.");
      return;
    }

    setError(null);
    setPreviewLoading(true);

    try {
      const preview = await courseService.previewGroupPartition(courseId, {
        group_set_name: groupSetName.trim(),
        mode,
        group_size: groupSize,
      });
      setDraftGroups(preview.groups);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Không thể tạo bản xem trước phân nhóm."
      );
    } finally {
      setPreviewLoading(false);
    }
  };

  const moveMember = (toGroupIdx: number) => {
    if (!dragPayload || !draftGroups) return;
    if (dragPayload.fromGroupIdx === toGroupIdx) {
      setDragPayload(null);
      return;
    }

    const updated = draftGroups.map((grp, idx) => {
      if (idx === dragPayload.fromGroupIdx) {
        return {
          ...grp,
          members: grp.members.filter((m) => m.user_id !== dragPayload.member.user_id),
        };
      }
      if (idx === toGroupIdx) {
        return {
          ...grp,
          members: [...grp.members, dragPayload.member],
        };
      }
      return grp;
    });
    setDraftGroups(updated);
    setDragPayload(null);
  };

  const handleSave = async () => {
    if (!draftGroups || draftGroups.length === 0) return;
    setSaving(true);
    setError(null);

    try {
      const saved = await courseService.saveGroupSet(courseId, groupSetName.trim(), {
        groups: draftGroups.map((g) => ({
          name: g.name,
          member_ids: g.members.map((m) => m.user_id),
        })),
      });
      showToast(
        "success",
        `Đã lưu bộ nhóm "${saved.group_set_name}" gồm ${saved.groups.length} nhóm!`
      );
      reset();
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không thể lưu bộ nhóm.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Phân chia nhóm học tập"
      subtitle="Xem trước danh sách nhóm và kéo thả sinh viên giữa các nhóm trước khi lưu"
      onClose={handleClose}
      maxWidthClass="max-w-4xl"
      footer={
        <>
          <MmButton variant="secondary" onClick={handleClose} disabled={saving}>
            Hủy bỏ
          </MmButton>
          <MmButton
            variant="brand"
            disabled={!draftGroups || draftGroups.length === 0}
            loading={saving}
            onClick={handleSave}
          >
            <Save className="h-4 w-4" />
            <span>Lưu bộ nhóm</span>
          </MmButton>
        </>
      }
    >
      <div className="space-y-5">
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="font-mm-ui text-sm">{error}</span>
          </div>
        )}

        <form
          onSubmit={handleGeneratePreview}
          className="grid grid-cols-1 gap-4 rounded-mm-panel border border-mm-border bg-mm-divider/30 p-4 md:grid-cols-12 md:items-end"
        >
          <div className="md:col-span-4">
            <FormField label="Tên bộ nhóm" htmlFor="group-set-name" required>
              <input
                id="group-set-name"
                type="text"
                value={groupSetName}
                onChange={(e) => setGroupSetName(e.target.value)}
                placeholder="vd: Nhóm Bài tập lớn"
                className={mmInputClass(false)}
              />
            </FormField>
          </div>

          <div className="md:col-span-4">
            <FormField label="Chế độ phân nhóm" htmlFor="group-mode" required>
              <select
                id="group-mode"
                value={mode}
                onChange={(e) => setMode(e.target.value as GroupingMode)}
                className={mmInputClass(false)}
              >
                {MODE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          <div className="md:col-span-2">
            <FormField label="SV / nhóm" htmlFor="group-size" required>
              <input
                id="group-size"
                type="number"
                min={2}
                max={10}
                value={groupSize}
                onChange={(e) => setGroupSize(Number(e.target.value))}
                className={mmInputClass(false)}
              />
            </FormField>
          </div>

          <div className="md:col-span-2">
            <MmButton
              type="submit"
              variant="primary"
              fullWidth
              loading={previewLoading}
            >
              <Shuffle className="h-4 w-4" />
              <span>Xem trước</span>
            </MmButton>
          </div>
        </form>

        {draftGroups && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="font-mm-ui text-sm font-medium text-mm-heading">
                Bản xem trước ({draftGroups.length} nhóm) — Kéo thả tên sinh viên để chuyển nhóm
              </p>
              <span className="font-mm-data text-xs text-mm-text-muted">
                Tổng cộng:{" "}
                {draftGroups.reduce((sum, g) => sum + g.members.length, 0)} sinh viên được xếp
              </span>
            </div>

            <div className="grid max-h-[420px] grid-cols-1 gap-4 overflow-y-auto pr-1 sm:grid-cols-2 lg:grid-cols-3">
              {draftGroups.map((group, groupIdx) => (
                <div
                  key={`${group.name}-${groupIdx}`}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => moveMember(groupIdx)}
                  className="flex flex-col rounded-mm-panel border border-mm-border bg-mm-bg p-3.5 transition-colors hover:border-mm-blue-hover/60"
                >
                  <div className="mb-2.5 flex items-center justify-between border-b border-mm-divider pb-2">
                    <span className="font-mm-ui text-sm font-semibold text-mm-heading">
                      {group.name}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-mm-divider px-2 py-0.5 font-mm-data text-xs text-mm-text-secondary">
                      <Users className="h-3 w-3" />
                      {group.members.length}
                    </span>
                  </div>

                  {group.members.length === 0 ? (
                    <p className="py-4 text-center font-mm-ui text-xs text-mm-text-muted">
                      Thả sinh viên vào đây
                    </p>
                  ) : (
                    <ul className="space-y-1.5">
                      {group.members.map((member) => (
                        <li
                          key={member.user_id}
                          draggable
                          onDragStart={() =>
                            setDragPayload({ fromGroupIdx: groupIdx, member })
                          }
                          className="flex cursor-grab items-center gap-2 rounded-mm-btn border border-mm-divider bg-mm-divider/30 px-2.5 py-1.5 text-xs active:cursor-grabbing"
                        >
                          <GripVertical className="h-3.5 w-3.5 shrink-0 text-mm-text-muted" />
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-mm-ui font-medium text-mm-heading">
                              {member.full_name}
                            </p>
                            {member.user_code && (
                              <p className="font-mm-mono text-[11px] text-mm-text-muted">
                                {member.user_code}
                              </p>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </MmModal>
  );
};
