/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertTriangle, Plus, Save, ShieldAlert, Trash2, X } from "lucide-react";
import { gradebookService } from "../../../../services/gradebookService";
import { ApiError } from "../../../../services/httpClient";
import type {
  GradebookStructureResponse,
  GradeGroupInputPayload,
  GradeItemType,
} from "../../../../types/gradebook";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";

interface GradebookStructureModalProps {
  open: boolean;
  courseId: string;
  structure: GradebookStructureResponse | null;
  onClose: () => void;
  onSaved: () => void;
}

interface EditableGroup extends GradeGroupInputPayload {
  localKey: string;
}

export const GradebookStructureModal: React.FC<GradebookStructureModalProps> = ({
  open,
  courseId,
  structure,
  onClose,
  onSaved,
}) => {
  const [groups, setGroups] = useState<EditableGroup[]>([]);
  const [saving, setSaving] = useState(false);

  // Add sub-column form (Subflow A-1)
  const [addingColGroupId, setAddingColGroupId] = useState<string | null>(null);
  const [newColTitle, setNewColTitle] = useState("");
  const [newColType, setNewColType] = useState<GradeItemType>("MANUAL");
  const [newColMaxPoints, setNewColMaxPoints] = useState(10);
  const [creatingCol, setCreatingCol] = useState(false);

  // Confirm delete group with grades (E-GB-01 -> type XOA)
  const [confirmDeleteGroup, setConfirmDeleteGroup] = useState<EditableGroup | null>(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deletingGroup, setDeletingGroup] = useState(false);

  useEffect(() => {
    if (!open || !structure) return;
    setGroups(
      structure.groups.map((g) => ({
        localKey: g.id,
        id: g.id,
        group_name: g.group_name,
        weight_percent: g.weight_percent,
        drop_lowest_count: g.drop_lowest_count,
        is_hurdle: g.is_hurdle,
        hurdle_min_score: Number(g.hurdle_min_score ?? 4.0),
      }))
    );
  }, [open, structure]);

  if (!open) return null;

  const totalWeight = groups.reduce((acc, g) => acc + (Number(g.weight_percent) || 0), 0);
  const isWeightValid = totalWeight === 100;
  const isLocked = Boolean(structure?.is_locked);

  const handleAddGroup = () => {
    setGroups((prev) => [
      ...prev,
      {
        localKey: `new-${Date.now()}-${prev.length}`,
        group_name: "Nhóm điểm mới",
        weight_percent: Math.max(1, 100 - totalWeight),
        drop_lowest_count: 0,
        is_hurdle: false,
        hurdle_min_score: 4.0,
      },
    ]);
  };

  const handleUpdateGroup = (index: number, patch: Partial<EditableGroup>) => {
    setGroups((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  };

  const handleRemoveGroupClick = (grp: EditableGroup, idx: number) => {
    if (!grp.id) {
      setGroups((prev) => prev.filter((_, i) => i !== idx));
      return;
    }
    setConfirmDeleteGroup(grp);
    setDeleteConfirmText("");
  };

  const handleConfirmDeleteGroup = async () => {
    if (!confirmDeleteGroup?.id) return;
    setDeletingGroup(true);
    try {
      await gradebookService.deleteGroup(courseId, confirmDeleteGroup.id, deleteConfirmText);
      showToast("success", `Đã xóa nhóm điểm "${confirmDeleteGroup.group_name}".`);
      setGroups((prev) => prev.filter((g) => g.id !== confirmDeleteGroup.id));
      setConfirmDeleteGroup(null);
      onSaved();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể xóa nhóm điểm."
      );
    } finally {
      setDeletingGroup(false);
    }
  };

  const handleSave = async () => {
    if (!isWeightValid || isLocked) return;
    setSaving(true);
    try {
      await gradebookService.saveStructure(
        courseId,
        groups.map(({ localKey: _k, ...rest }) => rest)
      );
      showToast("success", "Thiết lập cơ cấu sổ điểm thành công!");
      onSaved();
      onClose();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể lưu cơ cấu sổ điểm."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleCreateSubColumn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addingColGroupId || !newColTitle.trim()) return;
    setCreatingCol(true);
    try {
      await gradebookService.createColumn(courseId, {
        group_id: addingColGroupId,
        title: newColTitle.trim(),
        item_type: newColType,
        max_points: newColMaxPoints,
        is_muted: true,
      });
      showToast("success", `Đã thêm cột điểm "${newColTitle.trim()}" vào nhóm.`);
      setAddingColGroupId(null);
      setNewColTitle("");
      onSaved();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể thêm cột điểm.");
    } finally {
      setCreatingCol(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-mm-border bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-mm-divider pb-4">
          <div>
            <h2 className="font-mm-display text-xl font-semibold text-mm-heading">
              Cấu hình Cơ cấu Sổ điểm Động (T2-P-M5-01)
            </h2>
            <p className="mt-1 font-mm-ui text-xs text-mm-text-secondary">
              Tổng trọng số các nhóm điểm thành phần bắt buộc đạt chính xác 100% trước khi lưu.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-mm-text-secondary hover:bg-mm-divider"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Real-time Weight Balance Bar */}
        <div
          className={`mt-4 flex items-center justify-between rounded-xl border px-4 py-3 text-sm font-medium ${
            isWeightValid
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-amber-300 bg-amber-50 text-amber-900"
          }`}
        >
          <div className="flex items-center gap-2">
            {!isWeightValid && <AlertTriangle className="h-4 w-4 text-amber-600" />}
            <span>
              Tổng trọng số hiện tại: <strong className="font-mm-mono">{totalWeight}% / 100%</strong>
            </span>
          </div>
          <span className="text-xs">
            {isWeightValid
              ? "Đạt chuẩn trọng số 100%"
              : `Cần điều chỉnh ${totalWeight < 100 ? `tăng thêm ${100 - totalWeight}%` : `giảm bớt ${totalWeight - 100}%`} (E-11)`}
          </span>
        </div>

        {/* Grade Groups Table */}
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-mm-divider bg-slate-50 text-xs font-semibold text-mm-text-secondary">
                <th className="px-3 py-2.5">Tên nhóm điểm</th>
                <th className="w-28 px-3 py-2.5">Trọng số (%)</th>
                <th className="w-40 px-3 py-2.5">Bỏ điểm thấp nhất</th>
                <th className="w-44 px-3 py-2.5">Điểm liệt (Hurdle)</th>
                <th className="w-36 px-3 py-2.5 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-mm-divider">
              {groups.map((grp, idx) => (
                <tr key={grp.localKey} className="hover:bg-slate-50/70">
                  <td className="px-3 py-2.5">
                    <input
                      type="text"
                      disabled={isLocked}
                      value={grp.group_name}
                      onChange={(e) => handleUpdateGroup(idx, { group_name: e.target.value })}
                      className="w-full rounded-lg border border-mm-border px-2.5 py-1.5 text-sm focus:border-mm-blue-primary focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <input
                      type="number"
                      min={1}
                      max={100}
                      disabled={isLocked}
                      value={grp.weight_percent}
                      onChange={(e) =>
                        handleUpdateGroup(idx, { weight_percent: Number(e.target.value) })
                      }
                      className="w-20 rounded-lg border border-mm-border px-2.5 py-1.5 font-mm-mono text-sm"
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <label className="inline-flex items-center gap-2 text-xs text-mm-text-secondary">
                      <input
                        type="checkbox"
                        disabled={isLocked}
                        checked={grp.drop_lowest_count > 0}
                        onChange={(e) =>
                          handleUpdateGroup(idx, { drop_lowest_count: e.target.checked ? 1 : 0 })
                        }
                      />
                      <span>Bỏ 1 bài thấp nhất</span>
                    </label>
                  </td>
                  <td className="px-3 py-2.5">
                    <label className="inline-flex items-center gap-2 text-xs font-medium text-rose-700">
                      <input
                        type="checkbox"
                        disabled={isLocked}
                        checked={grp.is_hurdle}
                        onChange={(e) => handleUpdateGroup(idx, { is_hurdle: e.target.checked })}
                      />
                      <ShieldAlert className="h-3.5 w-3.5" />
                      <span>Hurdle (&ge; {grp.hurdle_min_score})</span>
                    </label>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <div className="inline-flex items-center gap-1">
                      {grp.id && !isLocked && (
                        <button
                          type="button"
                          onClick={() => setAddingColGroupId(grp.id ?? null)}
                          className="rounded-lg border border-mm-border px-2 py-1 text-xs font-medium text-mm-blue-primary hover:bg-blue-50"
                          title="Thêm cột điểm con"
                        >
                          + Cột
                        </button>
                      )}
                      {!isLocked && (
                        <button
                          type="button"
                          onClick={() => handleRemoveGroupClick(grp, idx)}
                          className="rounded-lg p-1.5 text-rose-600 hover:bg-rose-50"
                          title="Xóa nhóm điểm"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Subflow A-1: Inline Add Column Form */}
        {addingColGroupId && (
          <form
            onSubmit={handleCreateSubColumn}
            className="mt-4 rounded-xl border border-blue-200 bg-blue-50/50 p-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-mm-heading">Thêm cột điểm con vào nhóm</h3>
              <button
                type="button"
                onClick={() => setAddingColGroupId(null)}
                className="text-xs text-mm-text-secondary hover:underline"
              >
                Đóng
              </button>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <input
                type="text"
                required
                placeholder="VD: Bài tập thực hành Tuần 3"
                value={newColTitle}
                onChange={(e) => setNewColTitle(e.target.value)}
                className="rounded-lg border border-mm-border bg-white px-3 py-1.5 text-sm"
              />
              <select
                value={newColType}
                onChange={(e) => setNewColType(e.target.value as GradeItemType)}
                className="rounded-lg border border-mm-border bg-white px-3 py-1.5 text-sm"
              >
                <option value="MANUAL">Chấm thủ công</option>
                <option value="ASSIGNMENT">Nộp file kèm Viva</option>
                <option value="QUIZ">Trắc nghiệm trực tuyến</option>
                <option value="PROGRESS_ATTENDANCE">Chuyên cần học liệu</option>
              </select>
              <input
                type="number"
                min={1}
                max={100}
                value={newColMaxPoints}
                onChange={(e) => setNewColMaxPoints(Number(e.target.value))}
                className="rounded-lg border border-mm-border bg-white px-3 py-1.5 font-mm-mono text-sm"
              />
            </div>
            <div className="flex justify-end">
              <MmButton type="submit" variant="brand" size="sm" loading={creatingCol}>
                <span>Thêm vào nhóm</span>
              </MmButton>
            </div>
          </form>
        )}

        {/* E-GB-01 Delete Confirmation Box */}
        {confirmDeleteGroup && (
          <div className="mt-4 rounded-xl border border-rose-300 bg-rose-50 p-4 space-y-3">
            <p className="text-xs font-medium text-rose-800">
              Xác nhận xóa nhóm điểm &quot;{confirmDeleteGroup.group_name}&quot;. Nếu nhóm đã có dữ liệu
              điểm sinh viên, hãy gõ chính xác chữ <strong>XOA</strong> vào ô bên dưới:
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                placeholder="Gõ XOA để xác nhận"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                className="rounded-lg border border-rose-300 bg-white px-3 py-1.5 font-mm-mono text-sm"
              />
              <MmButton
                variant="danger"
                size="sm"
                loading={deletingGroup}
                onClick={handleConfirmDeleteGroup}
              >
                <span>Xác nhận xóa</span>
              </MmButton>
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => setConfirmDeleteGroup(null)}
              >
                <span>Hủy</span>
              </MmButton>
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-mm-divider pt-4">
          <MmButton variant="secondary" disabled={isLocked} onClick={handleAddGroup}>
            <Plus className="h-4 w-4" />
            <span>Thêm nhóm điểm mới</span>
          </MmButton>

          <div className="flex items-center gap-2">
            <MmButton variant="secondary" onClick={onClose}>
              <span>Đóng</span>
            </MmButton>
            <MmButton
              variant="brand"
              disabled={!isWeightValid || isLocked}
              loading={saving}
              onClick={handleSave}
              title={
                !isWeightValid
                  ? `Tổng trọng số hiện tại là ${totalWeight}%. Cần đạt đúng 100%`
                  : "Lưu cấu hình sổ điểm"
              }
            >
              <Save className="h-4 w-4" />
              <span>Lưu Cấu Hình Sổ Điểm</span>
            </MmButton>
          </div>
        </div>
      </div>
    </div>
  );
};
