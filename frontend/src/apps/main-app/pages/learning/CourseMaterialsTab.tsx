/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  BookmarkCheck,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  Eye,
  EyeOff,
  FileText,
  Film,
  FolderPlus,
  Lock,
  Plus,
  Presentation,
  Trash2,
} from "lucide-react";
import { learningService } from "../../../../services/learningService";
import { ApiError } from "../../../../services/httpClient";
import type { LOResponse } from "../../../../types/course";
import type { LearningMaterial, LearningModule, MaterialType } from "../../../../types/learning";
import { BloomBadge } from "../../components/BloomBadge";
import { ConfirmModal } from "../../components/ConfirmModal";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { showToast } from "../../components/Toast";
import { CheckpointEditorModal } from "./CheckpointEditorModal";
import { MaterialFormModal } from "./MaterialFormModal";
import { MaterialViewerModal } from "./MaterialViewerModal";
import { ModuleFormModal } from "./ModuleFormModal";

const MATERIAL_ICON: Record<MaterialType, React.ReactNode> = {
  SLIDE: <Presentation className="h-4 w-4 text-orange-500" />,
  PDF: <FileText className="h-4 w-4 text-red-500" />,
  VIDEO: <Film className="h-4 w-4 text-blue-500" />,
  DOCUMENT: <FileText className="h-4 w-4 text-emerald-500" />,
};

const formatDateTime = (isoStr: string) => {
  try {
    return new Date(isoStr).toLocaleString("vi-VN", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return isoStr;
  }
};

export interface CourseMaterialsTabProps {
  courseId: string;
  canEdit: boolean;
  availableLos: LOResponse[];
}

export const CourseMaterialsTab: React.FC<CourseMaterialsTabProps> = ({
  courseId,
  canEdit,
  availableLos,
}) => {
  const [modules, setModules] = useState<LearningModule[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [expandedModules, setExpandedModules] = useState<Record<string, boolean>>({});

  // Modals state
  const [moduleModalOpen, setModuleModalOpen] = useState(false);
  const [editingModule, setEditingModule] = useState<LearningModule | null>(null);

  const [materialModalOpen, setMaterialModalOpen] = useState(false);
  const [targetModuleId, setTargetModuleId] = useState<string>("");
  const [editingMaterial, setEditingMaterial] = useState<LearningMaterial | null>(null);
  const [checkpointMaterial, setCheckpointMaterial] = useState<LearningMaterial | null>(null);
  const [viewingMaterial, setViewingMaterial] = useState<LearningMaterial | null>(null);

  // Deletion confirm modals
  const [deletingModule, setDeletingModule] = useState<LearningModule | null>(null);
  const [deletingMaterial, setDeletingMaterial] = useState<LearningMaterial | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadModules = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await learningService.listModules(courseId);
      setModules(data);
      // Auto expand first 2 modules by default
      const initialExpanded: Record<string, boolean> = {};
      data.forEach((m, idx) => {
        initialExpanded[m.id] = idx < 2;
      });
      setExpandedModules((prev) => ({ ...initialExpanded, ...prev }));
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Không thể tải danh sách bài học.";
      setLoadError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    loadModules();
  }, [loadModules]);

  const toggleExpand = (modId: string) => {
    setExpandedModules((prev) => ({ ...prev, [modId]: !prev[modId] }));
  };

  const handleReorder = async (index: number, direction: -1 | 1) => {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= modules.length) return;

    const newList = [...modules];
    const [moved] = newList.splice(index, 1);
    newList.splice(targetIdx, 0, moved);

    setModules(newList);
    try {
      const reordered = await learningService.reorderModules(
        courseId,
        newList.map((m) => m.id)
      );
      setModules(reordered);
      showToast("success", "Đã cập nhật thứ tự bài học.");
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Lỗi khi sắp xếp bài học.");
      await loadModules();
    }
  };

  const handleToggleModulePublish = async (mod: LearningModule) => {
    try {
      const updated = await learningService.toggleModulePublish(courseId, mod.id, !mod.is_published);
      setModules((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
      showToast("success", `Đã ${updated.is_published ? "xuất bản" : "chuyển về nháp"} bài học.`);
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Lỗi khi đổi trạng thái bài học.");
    }
  };

  const handleDeleteModule = async () => {
    if (!deletingModule) return;
    setActionLoading(true);
    try {
      await learningService.deleteModule(courseId, deletingModule.id);
      showToast("success", `Đã xóa bài học: ${deletingModule.title}`);
      setDeletingModule(null);
      await loadModules();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể xóa bài học.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleMaterialPublish = async (mat: LearningMaterial) => {
    try {
      const updated = await learningService.toggleMaterialPublish(courseId, mat.id, !mat.is_published);
      setModules((prev) =>
        prev.map((m) => {
          if (m.id === updated.module_id) {
            return {
              ...m,
              materials: m.materials.map((x) => (x.id === updated.id ? updated : x)),
            };
          }
          return m;
        })
      );
      showToast("success", `Đã ${updated.is_published ? "công bố" : "ẩn"} học liệu.`);
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Lỗi khi cập nhật học liệu.");
    }
  };

  const handleDeleteMaterial = async () => {
    if (!deletingMaterial) return;
    setActionLoading(true);
    try {
      await learningService.deleteMaterial(courseId, deletingMaterial.id);
      showToast("success", `Đã xóa học liệu: ${deletingMaterial.title}`);
      setDeletingMaterial(null);
      await loadModules();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể xóa học liệu.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownloadMaterial = async (mat: LearningMaterial) => {
    if (!mat.file_url) return;
    if (mat.file_url.startsWith("http://") || mat.file_url.startsWith("https://")) {
      window.open(mat.file_url, "_blank");
      return;
    }
    const ext = mat.file_url.split(".").pop() || "bin";
    const filename = `${mat.title}.${ext}`;
    try {
      await learningService.downloadMaterialFile(courseId, mat.id, filename);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải xuống tệp học liệu."
      );
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-mm-brand border-t-transparent" />
        <p className="font-mm-ui text-sm text-mm-text-muted">Đang tải danh sách bài học và học liệu...</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <MmCard variant="standard" radius="card" padding="lg">
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <AlertCircle className="mb-3 h-10 w-10 text-mm-danger" />
          <h3 className="font-mm-mid text-base font-medium text-mm-heading">
            Không thể tải dữ liệu học liệu
          </h3>
          <p className="mt-1 max-w-md font-mm-ui text-sm text-mm-text-secondary">{loadError}</p>
          <MmButton variant="secondary" className="mt-4" onClick={loadModules}>
            Thử lại
          </MmButton>
        </div>
      </MmCard>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col justify-between gap-4 border-b border-mm-divider pb-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="font-mm-mid text-[22px] font-semibold text-mm-heading">
            Học liệu & Cấu trúc Bài học
          </h2>
          <p className="mt-1 font-mm-ui text-sm text-mm-text-secondary">
            Danh mục các chương, bài giảng đa phương tiện và tài liệu chuẩn đầu ra (BR-LO-01)
          </p>
        </div>

        {canEdit && (
          <MmButton
            variant="brand"
            onClick={() => {
              setEditingModule(null);
              setModuleModalOpen(true);
            }}
          >
            <FolderPlus className="h-4 w-4" />
            <span>Thêm chương/bài học</span>
          </MmButton>
        )}
      </div>

      {/* Modules list */}
      {modules.length === 0 ? (
        <MmCard variant="standard" radius="card" padding="lg">
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Presentation className="h-12 w-12 text-mm-text-muted mb-3" />
            <h3 className="font-mm-mid text-lg font-medium text-mm-heading">
              Chưa có bài học nào trong môn học này
            </h3>
            <p className="mt-1 text-sm text-mm-text-secondary max-w-md">
              {canEdit
                ? "Bắt đầu thiết kế khóa học bằng cách tạo chương đầu tiên và tải lên slide, tài liệu hoặc video bài giảng."
                : "Giảng viên chưa công bố bài học nào cho môn học này."}
            </p>
            {canEdit && (
              <MmButton
                variant="brand"
                className="mt-4"
                onClick={() => {
                  setEditingModule(null);
                  setModuleModalOpen(true);
                }}
              >
                <Plus className="h-4 w-4" />
                <span>Tạo bài học đầu tiên</span>
              </MmButton>
            )}
          </div>
        </MmCard>
      ) : (
        <div className="space-y-4">
          {modules.map((mod, idx) => {
            const isExpanded = Boolean(expandedModules[mod.id]);
            const isLocked = mod.is_locked;

            return (
              <div
                key={mod.id}
                className="overflow-hidden rounded-mm-lg border border-mm-divider bg-mm-surface transition-all"
              >
                {/* Module Header Bar */}
                <div
                  className={`flex flex-wrap items-center justify-between gap-3 p-4 select-none ${
                    isLocked ? "bg-mm-surface-alt/70 opacity-90" : "bg-mm-surface"
                  }`}
                >
                  <div
                    className="flex flex-1 items-center gap-3 cursor-pointer"
                    onClick={() => toggleExpand(mod.id)}
                  >
                    <button
                      type="button"
                      className="text-mm-text-muted hover:text-mm-text-primary p-1"
                      aria-label="Toggle module accordion"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-5 w-5" />
                      ) : (
                        <ChevronRight className="h-5 w-5" />
                      )}
                    </button>

                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-mm-surface-alt text-xs font-semibold text-mm-text-secondary border border-mm-divider">
                      {mod.order_index}
                    </span>

                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-mm-mid text-base font-semibold text-mm-heading">
                          {mod.title}
                        </h3>

                        {isLocked && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600 border border-amber-500/20">
                            <Lock className="h-3 w-3" />
                            <span>Khóa</span>
                          </span>
                        )}

                        {!mod.is_published && (
                          <span className="inline-flex items-center rounded-full bg-mm-btn-secondary px-2.5 py-0.5 text-xs font-medium text-mm-text-secondary border border-mm-divider">
                            Bản nháp
                          </span>
                        )}
                      </div>

                      {/* Lock Reason or Prerequisite Info */}
                      {isLocked && mod.lock_reason && (
                        <p className="mt-0.5 flex items-center gap-1 text-xs text-amber-600">
                          <AlertCircle className="h-3 w-3" />
                          <span>{mod.lock_reason}</span>
                        </p>
                      )}

                      {!isLocked && mod.prerequisite_title && (
                        <p className="mt-0.5 text-xs text-mm-text-muted">
                          Yêu cầu tiên quyết:{" "}
                          <span className="font-medium text-mm-text-secondary">
                            {mod.prerequisite_title}
                          </span>
                        </p>
                      )}

                      {mod.unlock_at && (
                        <p className="mt-0.5 flex items-center gap-1 text-xs text-blue-600">
                          <Clock className="h-3 w-3" />
                          <span>Lịch mở khóa: {formatDateTime(mod.unlock_at)}</span>
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Instructor Controls */}
                  {canEdit && (
                    <div className="flex items-center gap-1">
                      <MmButton
                        variant="ghost"
                        size="sm"
                        disabled={idx === 0}
                        onClick={() => handleReorder(idx, -1)}
                        title="Di chuyển lên trên"
                      >
                        <ArrowUp className="h-3.5 w-3.5" />
                      </MmButton>
                      <MmButton
                        variant="ghost"
                        size="sm"
                        disabled={idx === modules.length - 1}
                        onClick={() => handleReorder(idx, 1)}
                        title="Di chuyển xuống dưới"
                      >
                        <ArrowDown className="h-3.5 w-3.5" />
                      </MmButton>

                      <MmButton
                        variant="ghost"
                        size="sm"
                        onClick={() => handleToggleModulePublish(mod)}
                        title={mod.is_published ? "Chuyển về bản nháp" : "Xuất bản bài học"}
                      >
                        {mod.is_published ? (
                          <Eye className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <EyeOff className="h-4 w-4 text-mm-text-muted" />
                        )}
                      </MmButton>

                      <MmButton
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setTargetModuleId(mod.id);
                          setEditingMaterial(null);
                          setMaterialModalOpen(true);
                        }}
                      >
                        <Plus className="h-3.5 w-3.5" />
                        <span>Thêm học liệu</span>
                      </MmButton>

                      <MmButton
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingModule(mod);
                          setModuleModalOpen(true);
                        }}
                      >
                        Sửa
                      </MmButton>

                      <MmButton
                        variant="ghost"
                        size="sm"
                        className="text-mm-error hover:bg-mm-error-bg"
                        onClick={() => setDeletingModule(mod)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </MmButton>
                    </div>
                  )}
                </div>

                {/* Module Materials Accordion Body */}
                {isExpanded && (
                  <div className="border-t border-mm-divider bg-mm-surface/50 p-4">
                    {isLocked ? (
                      <div className="flex items-center justify-center gap-2 py-6 text-sm text-mm-text-muted">
                        <Lock className="h-4 w-4 text-amber-500" />
                        <span>{mod.lock_reason || "Nội dung bài học đang tạm khóa đối với sinh viên."}</span>
                      </div>
                    ) : mod.materials.length === 0 ? (
                      <div className="py-6 text-center text-sm text-mm-text-muted">
                        Chưa có học liệu nào trong bài học này.{" "}
                        {canEdit && (
                          <button
                            type="button"
                            className="font-medium text-mm-brand underline hover:opacity-80"
                            onClick={() => {
                              setTargetModuleId(mod.id);
                              setEditingMaterial(null);
                              setMaterialModalOpen(true);
                            }}
                          >
                            Tải lên học liệu đầu tiên
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="divide-y divide-mm-divider rounded-mm border border-mm-divider bg-mm-surface">
                        {mod.materials.map((mat) => {
                          const matchingLo = availableLos.find((lo) => lo.id === mat.lo_id);

                          return (
                            <div
                              key={mat.id}
                              className="flex flex-wrap items-center justify-between gap-3 p-3.5 transition-colors hover:bg-mm-surface-alt/40"
                            >
                              <div className="flex items-center gap-3">
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-mm bg-mm-surface-alt border border-mm-divider">
                                  {MATERIAL_ICON[mat.material_type] || <FileText className="h-4 w-4" />}
                                </div>

                                <div>
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <button
                                      type="button"
                                      onClick={() => mat.file_url && setViewingMaterial(mat)}
                                      className={`text-left font-mm-mid text-sm font-medium text-mm-heading ${
                                        mat.file_url ? "hover:text-mm-brand hover:underline cursor-pointer" : "cursor-default"
                                      }`}
                                    >
                                      {mat.title}
                                    </button>

                                    {mat.is_mandatory && (
                                      <span className="rounded bg-rose-500/10 px-2 py-0.5 text-[11px] font-semibold text-rose-600 border border-rose-500/20">
                                        Bắt buộc
                                      </span>
                                    )}

                                    {matchingLo && (
                                      <span className="flex items-center gap-1.5">
                                        <span className="font-mm-mono text-[11px] font-semibold text-mm-primary">
                                          {matchingLo.code}
                                        </span>
                                        <BloomBadge level={matchingLo.bloom_level} />
                                      </span>
                                    )}

                                    {!mat.is_published && (
                                      <span className="rounded bg-mm-surface-alt px-1.5 py-0.5 text-[11px] text-mm-text-muted border border-mm-divider">
                                        Ẩn
                                      </span>
                                    )}
                                  </div>

                                  <div className="mt-1 flex items-center gap-3 text-xs text-mm-text-muted">
                                    <span className="flex items-center gap-1">
                                      <Clock className="h-3 w-3" />
                                      {mat.est_duration_minutes} phút
                                    </span>
                                    <span>•</span>
                                    <span>Định dạng: {mat.material_type}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Material Actions */}
                              <div className="flex items-center gap-1">
                                {mat.file_url && (
                                  <>
                                    <MmButton
                                      variant="primary"
                                      size="sm"
                                      onClick={() => setViewingMaterial(mat)}
                                    >
                                      <Eye className="h-3.5 w-3.5" />
                                      <span>Xem</span>
                                    </MmButton>
                                    <MmButton
                                      variant="secondary"
                                      size="sm"
                                      onClick={() => handleDownloadMaterial(mat)}
                                    >
                                      <Download className="h-3.5 w-3.5" />
                                      <span>Tải về</span>
                                    </MmButton>
                                  </>
                                )}

                                {canEdit && (
                                  <>
                                    <MmButton
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleToggleMaterialPublish(mat)}
                                      title={mat.is_published ? "Ẩn học liệu" : "Công bố học liệu"}
                                    >
                                      {mat.is_published ? (
                                        <Eye className="h-3.5 w-3.5 text-emerald-500" />
                                      ) : (
                                        <EyeOff className="h-3.5 w-3.5 text-mm-text-muted" />
                                      )}
                                    </MmButton>

                                    <MmButton
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => setCheckpointMaterial(mat)}
                                      title="Biên tập điểm dừng & Gợi ý câu hỏi AI"
                                    >
                                      <BookmarkCheck className="h-3.5 w-3.5 text-amber-500" />
                                    </MmButton>

                                    <MmButton
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => {
                                        setTargetModuleId(mod.id);
                                        setEditingMaterial(mat);
                                        setMaterialModalOpen(true);
                                      }}
                                    >
                                      Sửa
                                    </MmButton>

                                    <MmButton
                                      variant="ghost"
                                      size="sm"
                                      className="text-mm-error hover:bg-mm-error-bg"
                                      onClick={() => setDeletingMaterial(mat)}
                                    >
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </MmButton>
                                  </>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modals */}
      <ModuleFormModal
        open={moduleModalOpen}
        courseId={courseId}
        existingModules={modules}
        editingModule={editingModule}
        onClose={() => {
          setModuleModalOpen(false);
          setEditingModule(null);
        }}
        onSaved={loadModules}
      />

      <MaterialFormModal
        open={materialModalOpen}
        courseId={courseId}
        moduleId={targetModuleId}
        availableLos={availableLos}
        editingMaterial={editingMaterial}
        onClose={() => {
          setMaterialModalOpen(false);
          setEditingMaterial(null);
        }}
        onSaved={loadModules}
      />

      <ConfirmModal
        open={Boolean(deletingModule)}
        title="Xác nhận xóa bài học"
        description={`Bạn có chắc chắn muốn xóa bài học "${deletingModule?.title}"? Tất cả học liệu bên trong cũng sẽ bị xóa vĩnh viễn.`}
        confirmLabel={actionLoading ? "Đang xóa..." : "Xác nhận xóa"}
        danger
        loading={actionLoading}
        onCancel={() => setDeletingModule(null)}
        onConfirm={handleDeleteModule}
      />

      <ConfirmModal
        open={Boolean(deletingMaterial)}
        title="Xác nhận xóa học liệu"
        description={`Bạn có chắc chắn muốn xóa học liệu "${deletingMaterial?.title}" khỏi bài học?`}
        confirmLabel={actionLoading ? "Đang xóa..." : "Xác nhận xóa"}
        danger
        loading={actionLoading}
        onCancel={() => setDeletingMaterial(null)}
        onConfirm={handleDeleteMaterial}
      />

      <CheckpointEditorModal
        open={Boolean(checkpointMaterial)}
        courseId={courseId}
        material={checkpointMaterial}
        availableLos={availableLos}
        onClose={() => setCheckpointMaterial(null)}
      />

      <MaterialViewerModal
        open={Boolean(viewingMaterial)}
        courseId={courseId}
        material={viewingMaterial}
        matchingLo={availableLos.find((lo) => lo.id === viewingMaterial?.lo_id)}
        onClose={() => {
          setViewingMaterial(null);
          if (!canEdit) {
            loadModules();
          }
        }}
        onDownload={handleDownloadMaterial}
      />
    </div>
  );
};
