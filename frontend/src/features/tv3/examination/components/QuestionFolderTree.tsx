// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { Folder, FolderPlus, Trash2, ChevronRight, ChevronDown, Layers } from "lucide-react";
import { EduButton, EduCard, EduInput, EduModal } from "../../../../design-system";
import type { QuestionFolderResponse, QuestionFolderStatsResponse } from "../../../../types/examination";

export interface QuestionFolderTreeProps {
  folders: QuestionFolderResponse[];
  selectedFolderId?: string | null;
  stats?: QuestionFolderStatsResponse;
  onSelectFolder: (folderId: string | null) => void;
  onCreateFolder: (name: string, parentId?: string | null) => Promise<void>;
  onDeleteFolder: (folderId: string) => Promise<void>;
}

export const QuestionFolderTree: React.FC<QuestionFolderTreeProps> = ({
  folders,
  selectedFolderId,
  stats,
  onSelectFolder,
  onCreateFolder,
  onDeleteFolder,
}) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [parentFolderId, setParentFolderId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [collapsedMap, setCollapsedMap] = useState<Record<string, boolean>>({});

  const toggleCollapse = (folderId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCollapsedMap((prev) => ({ ...prev, [folderId]: !prev[folderId] }));
  };

  const handleOpenCreateModal = (parentId: string | null = null, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setParentFolderId(parentId);
    setNewFolderName("");
    setModalOpen(true);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;

    setIsSubmitting(true);
    try {
      await onCreateFolder(newFolderName.trim(), parentFolderId);
      setModalOpen(false);
      setNewFolderName("");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Nhóm thư mục gốc và thư mục con
  const rootFolders = folders.filter((f) => !f.parent_folder_id);
  const getSubFolders = (parentId: string) => folders.filter((f) => f.parent_folder_id === parentId);

  return (
    <EduCard variant="surface" padding="none" className="overflow-hidden border border-[rgba(15,34,54,0.12)]">
      <div className="p-3.5 bg-[#f5fbfd] border-b border-[rgba(15,34,54,0.08)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-[#006699]" />
          <h3 className="text-sm font-bold text-[#0f2236]">Thư mục Ngân hàng</h3>
        </div>
        <EduButton
          variant="secondary"
          size="sm"
          onClick={() => handleOpenCreateModal(null)}
          title="Tạo thư mục mới"
        >
          <FolderPlus className="w-3.5 h-3.5 mr-1" />
          <span>Thêm</span>
        </EduButton>
      </div>

      <div className="p-2 space-y-1">
        {/* Mục Tất cả câu hỏi */}
        <div
          onClick={() => onSelectFolder(null)}
          className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer transition-colors ${
            selectedFolderId === null
              ? "bg-[#eaf6fa] text-[#006699] font-bold"
              : "text-[#0f2236] hover:bg-[#f5fbfd]"
          }`}
        >
          <div className="flex items-center gap-2">
            <Folder className="w-4 h-4 text-[#7fbbdd]" />
            <span>Tất cả câu hỏi</span>
          </div>
          <span className="px-2 py-0.5 rounded-full bg-white border border-[rgba(15,34,54,0.1)] text-[11px] font-mono">
            {stats?.total_questions || 0}
          </span>
        </div>

        {/* Cây thư mục */}
        {rootFolders.map((rf) => {
          const subFolders = getSubFolders(rf.id);
          const isCollapsed = collapsedMap[rf.id];
          const isSelected = selectedFolderId === rf.id;
          const count = stats?.by_folder?.[rf.id] || 0;

          return (
            <div key={rf.id} className="space-y-1">
              <div
                onClick={() => onSelectFolder(rf.id)}
                className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer transition-colors ${
                  isSelected
                    ? "bg-[#eaf6fa] text-[#006699] font-bold"
                    : "text-[#0f2236] hover:bg-[#f5fbfd]"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {subFolders.length > 0 ? (
                    <button
                      type="button"
                      onClick={(e) => toggleCollapse(rf.id, e)}
                      className="p-0.5 hover:bg-black/5 rounded"
                      aria-label="Thu gọn hoặc mở rộng thư mục"
                    >
                      {isCollapsed ? (
                        <ChevronRight className="w-3.5 h-3.5 text-[#4a5f75]" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-[#4a5f75]" />
                      )}
                    </button>
                  ) : (
                    <span className="w-3.5" />
                  )}
                  <Folder className="w-4 h-4 text-[#f58b05] shrink-0" />
                  <span className="truncate">{rf.folder_name}</span>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="px-1.5 py-0.5 rounded-full bg-white border border-[rgba(15,34,54,0.1)] text-[10px] font-mono">
                    {count}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => handleOpenCreateModal(rf.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-[#006699] transition-opacity"
                    title="Thêm thư mục con"
                  >
                    <FolderPlus className="w-3 h-3" />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Xóa thư mục "${rf.folder_name}"?`)) {
                        onDeleteFolder(rf.id);
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-[#b91c1c] transition-opacity"
                    title="Xóa thư mục"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* Subfolders */}
              {!isCollapsed && subFolders.length > 0 && (
                <div className="pl-6 space-y-1 border-l-2 border-[rgba(127,187,221,0.3)] ml-4">
                  {subFolders.map((sub) => {
                    const isSubSelected = selectedFolderId === sub.id;
                    const subCount = stats?.by_folder?.[sub.id] || 0;

                    return (
                      <div
                        key={sub.id}
                        onClick={() => onSelectFolder(sub.id)}
                        className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
                          isSubSelected
                            ? "bg-[#eaf6fa] text-[#006699] font-bold"
                            : "text-[#4a5f75] hover:text-[#0f2236] hover:bg-[#f5fbfd]"
                        }`}
                      >
                        <div className="flex items-center gap-1.5 truncate">
                          <Folder className="w-3.5 h-3.5 text-[#7fbbdd] shrink-0" />
                          <span className="truncate">{sub.folder_name}</span>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <span className="px-1.5 py-0.2 rounded-full bg-white text-[10px] font-mono">
                            {subCount}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm(`Xóa thư mục "${sub.folder_name}"?`)) {
                                onDeleteFolder(sub.id);
                              }
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1 hover:text-[#b91c1c] transition-opacity"
                            title="Xóa thư mục con"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Modal tạo thư mục */}
      <EduModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={parentFolderId ? "Tạo thư mục con" : "Tạo thư mục mới"}
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <EduInput
            label="Tên thư mục"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            placeholder="Ví dụ: Chương 1 - Giới thiệu hệ thống"
            required
            autoFocus
          />
          <div className="flex justify-end gap-2 pt-2">
            <EduButton
              type="button"
              variant="secondary"
              onClick={() => setModalOpen(false)}
            >
              Hủy
            </EduButton>
            <EduButton
              type="submit"
              variant="primary"
              disabled={isSubmitting || !newFolderName.trim()}
            >
              {isSubmitting ? "Đang tạo..." : "Xác nhận tạo"}
            </EduButton>
          </div>
        </form>
      </EduModal>
    </EduCard>
  );
};
